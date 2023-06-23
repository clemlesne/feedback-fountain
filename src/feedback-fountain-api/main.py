# Init environment variables
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


# Import modules
from azure.cosmos import CosmosClient
from tenacity import retry, stop_after_attempt
from azure.identity import DefaultAzureCredential
import azure.ai.contentsafety as azure_cs
import azure.core.exceptions as azure_exceptions
from azure.core.credentials import AzureKeyCredential
from azure.cosmos.exceptions import CosmosResourceExistsError
from pydantic import BaseModel, ValidationError
from datetime import datetime
from fastapi import (
    FastAPI,
    status,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from models.feedback import FeedbackModel, SearchFeedbackModel
from models.like import LikeModel, SearchLikeModel
from models.comment import CommentModel, SearchCommentModel
from qdrant_client import QdrantClient
from typing import Union
from uuid import UUID, uuid4
import asyncio
import logging
import openai
import os
import qdrant_client.http.models as qmodels


###
# Init misc
###

VERSION = os.environ.get("VERSION")

###
# Init logging
###

LOGGING_SYS_LEVEL = os.environ.get("MS_LOGGING_SYS_LEVEL", logging.WARN)
logging.basicConfig(level=LOGGING_SYS_LEVEL)

LOGGING_APP_LEVEL = os.environ.get("MS_LOGGING_APP_LEVEL", logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_APP_LEVEL)

###
# Init CosmosDB
###

COSMOSDB_URL = os.environ.get("MS_COSMOSDB_URL")
cosmos_client = CosmosClient(COSMOSDB_URL, DefaultAzureCredential()).get_database_client("feedback-fountain")
comment_client = cosmos_client.get_container_client("comments")
feedback_client = cosmos_client.get_container_client("feedbacks")
like_client = cosmos_client.get_container_client("likes")
user_client = cosmos_client.get_container_client("users")

###
# Init OpenAI
###

async def refresh_oai_token():
    """
    Refresh OpenAI token every 25 minutes.

    The OpenAI SDK does not support token refresh, so we need to do it manually. We passe manually the token to the SDK. Azure AD tokens are valid for 30 mins, but we refresh every 25 minutes to be safe.

    See: https://github.com/openai/openai-python/pull/350#issuecomment-1489813285
    """
    while True:
        logger.info("(OpenAI) Refreshing token")
        oai_cred = DefaultAzureCredential()
        oai_token = oai_cred.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_key = oai_token.token
        # Execute every 25 minutes
        await asyncio.sleep(25*60)


OAI_EMBEDDING_ARGS = {
    "deployment_id": os.environ.get("MS_OAI_ADA_DEPLOY_ID"),
    "model": "text-embedding-ada-002",
}
OAI_COMPLETION_ARGS = {
    "deployment_id": os.environ.get("MS_OAI_GPT_DEPLOY_ID"),
    "model": "gpt-3.5-turbo",
}

logger.info(f"(OpenAI) Using Aure private service \"{openai.api_base}\"")
openai.api_type = "azure_ad"
openai.api_version = "2023-05-15"
asyncio.create_task(refresh_oai_token())

###
# Init Azure Content Safety
###

# Score are following: 0 - Safe, 2 - Low, 4 - Medium, 6 - High
# See: https://review.learn.microsoft.com/en-us/azure/cognitive-services/content-safety/concepts/harm-categories?branch=release-build-content-safety#severity-levels
ACS_SEVERITY_THRESHOLD = 2
ACS_API_BASE = os.environ.get("MS_ACS_API_BASE")
ACS_API_TOKEN = os.environ.get("MS_ACS_API_TOKEN")
logger.info(f"(Azure Content Safety) Using Aure private service \"{ACS_API_BASE}\"")
acs_client = azure_cs.ContentSafetyClient(
    ACS_API_BASE, AzureKeyCredential(ACS_API_TOKEN)
)

###
# Init FastAPI
###

ROOT_PATH = os.environ.get("MS_ROOT_PATH", "")
logger.info(f'Using root path: "{ROOT_PATH}"')

api = FastAPI(
    contact={
        "url": "https://github.com/clemlesne/feedback-fountain",
    },
    description="Feedback Fountain API",
    license_info={
        "name": "Apache-2.0",
        "url": "https://github.com/clemlesne/feedback-fountain/blob/master/LICENCE",
    },
    root_path=ROOT_PATH,
    title="feedback-fountain-api",
    version=VERSION,
)

# Setup CORS
api.add_middleware(
    CORSMiddleware,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_origins=["*"],
)

###
# Init Qdrant
###

QD_COLLECTION = "moaw"
QD_DIMENSION = 1536
QD_METRIC = qmodels.Distance.DOT
QD_HOST = os.environ.get("MS_QD_HOST")
qd_client = QdrantClient(host=QD_HOST, port=6333)

# Ensure collection exists
try:
    qd_client.get_collection(QD_COLLECTION)
except Exception:
    qd_client.create_collection(
        collection_name=QD_COLLECTION,
        vectors_config=qmodels.VectorParams(
            distance=QD_METRIC,
            size=QD_DIMENSION,
        ),
    )


@api.get(
    "/health/liveness",
    status_code=status.HTTP_204_NO_CONTENT,
    name="Healthckeck liveness",
)
async def health_liveness_get() -> None:
    return None


@api.get("/like")
async def like_get_all_by_related(related: UUID) -> SearchLikeModel:
    res = like_client.query_items(
        query="SELECT * FROM c",
        partition_key=related.hex,
    )
    models = []
    for item in res:
        try:
            models.append(LikeModel(**item))
        except ValidationError:
            logger.warning(f"Invalid like: {item}")
    return SearchLikeModel(likes=models)


@api.post("/like", status_code=status.HTTP_201_CREATED)
async def like_post(like: LikeModel) -> LikeModel:
    like.id = uuid4()
    like.created = datetime.utcnow()

    try:
        like_client.upsert_item(body=cosmosdb_dict(like.dict()))
    except CosmosResourceExistsError:
        logger.warning(f"Like already exists: {like}")
        return Response(status_code=status.HTTP_409_CONFLICT)
    return like


@api.get("/feedback")
async def feedback_get_all() -> SearchFeedbackModel:
    res = feedback_client.query_items(
        query="SELECT * FROM c",
        enable_cross_partition_query=True,
    )
    models = []
    for item in res:
        try:
            models.append(FeedbackModel(**item))
        except ValidationError:
            logger.warning(f"Invalid feedback: {item}")
    return SearchFeedbackModel(feedbacks=models)


@api.get("/feedback/{id}")
async def feedback_get_one(id: UUID) -> Union[FeedbackModel, None]:
    res = feedback_client.read_item(item=id.hex, partition_key=id.hex)

    if res is None:
        return None

    return FeedbackModel(**res)


@api.post("/feedback", status_code=status.HTTP_201_CREATED)
async def feedback_post(feedback: FeedbackModel) -> FeedbackModel:
    for field in [feedback.title, feedback.content]:
        if await is_moderated(field):
            logger.debug(f"Field \"{field}\" is moderated")
            return Response(status_code=status.HTTP_204_NO_CONTENT)

    feedback.id = uuid4()
    feedback.created = datetime.utcnow()

    feedback_client.upsert_item(body=cosmosdb_dict(feedback.dict()))

    return await feedback_get_one(feedback.id)


@retry(stop=stop_after_attempt(3))
async def is_moderated(prompt: str) -> bool:
    logger.debug(f"Checking moderation for text: {prompt}")

    req = azure_cs.models.AnalyzeTextOptions(
        text=prompt,
        categories=[
            azure_cs.models.TextCategory.HATE,
            azure_cs.models.TextCategory.SELF_HARM,
            azure_cs.models.TextCategory.SEXUAL,
            azure_cs.models.TextCategory.VIOLENCE,
        ],
    )

    try:
        res = acs_client.analyze_text(req)
    except azure_exceptions.ClientAuthenticationError as e:
        logger.exception(e)
        return False

    logger.debug(f"Moderation result: {res}")
    return any(
        cat.severity >= ACS_SEVERITY_THRESHOLD
        for cat in [
            res.hate_result,
            res.self_harm_result,
            res.sexual_result,
            res.violence_result,
        ]
    )


def cosmosdb_dict(model: dict) -> dict:
        """
        Allow to use the dict() method on objects with CosmosDB SDK.
        """
        data = model.copy()

        for key, value in data.items():
            # CosmosDB requires the datetime fields to be ISO 8601 strings
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            # CosmosDB requires the UUID field to be a string
            elif isinstance(value, UUID):
                data[key] = value.hex
            elif isinstance(value, dict):
                data[key] = cosmosdb_dict(value)
            elif isinstance(value, list):
                data[key] = [cosmosdb_dict(item) if isinstance(item, dict) else item for item in value]
            elif isinstance(value, BaseModel):
                data[key] = cosmosdb_dict(value.dict())

        return data
