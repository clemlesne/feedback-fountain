import "./result.scss";
import API_BASE_URL from "./constants.jsx";
import axios from "axios";
import moment from "moment";
import PropTypes from "prop-types"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm";
import { useState, useMemo } from "react";

function Result({ feedback }) {
  // State
  const [likes, setLikes] = useState(null);

  const fetchLikes = async () => {
    await axios
      .get(`${API_BASE_URL}/like`, {
        params: {
          related: feedback.id,
        },
        timeout: 30000,
      })
      .then((res) => {
        if (res.data) {
          setLikes(res.data.likes);
        }
      })
      .catch((err) => {
        console.error(err);
      });
  };

  const sendLike = async () => {
    await axios
      .post(`${API_BASE_URL}/like`, {
        user: "00000000-0000-0000-0000-000000000000",
        related: feedback.id,
      })
      .catch((err) => {
        console.error(err);
      });

    fetchLikes();
  }

  useMemo(() => {
    fetchLikes();
  }, []);

  return (
    <div className="result">
      <h2 className="result__title">{feedback.title}</h2>
      <ReactMarkdown className="result__description" linkTarget="_blank" remarkPlugins={[remarkGfm]} children={feedback.content} />
      <small>{moment(feedback.created).format("l")}</small>
      {likes && <small>Liked by {likes.length}</small>}
      <a onClick={sendLike} href="#">Like</a>
    </div>
  );
}

Result.propTypes = {
  feedback: PropTypes.object.isRequired,
}

export default Result;
