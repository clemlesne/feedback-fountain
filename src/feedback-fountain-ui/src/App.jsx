import "./app.scss";
import { Helmet } from "react-helmet-async";
import { helmetJsonLdProp } from "react-schemaorg";
import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import FingerprintJS from "@fingerprintjs/fingerprintjs";
import Result from "./Result";
import SearchBar from "./SearchBar";
import useLocalStorageState from "use-local-storage-state";
import API_BASE_URL from "./constants.jsx";

function App() {
  // State
  const [feedbacks, setFeedbacks] = useState(null);
  // Persistance
  const [F, setF] = useLocalStorageState("F", { defaultValue: null });

  // Init the FingerPrintJS from the browser
  useMemo(() => {
    FingerprintJS.load()
      .then((fp) => fp.get())
      .then((res) => setF(res.visitorId));
  }, []);

  const fetchFeedbacks = async (value) => {
    await axios
      .get(`${API_BASE_URL}/feedback`, {
        // params: {
        //   limit: 10,
        //   query: value,
        //   user: F,
        // },
        timeout: 30000,
      })
      .then((res) => {
        if (res.data) {
          setFeedbacks(res.data.feedbacks);
        }
      });
  };

  return (
    <>
      <Helmet script={[
        helmetJsonLdProp({
          "@context": "https://schema.org",
          "@type": "WebApplication",
          alternateName: "MOAW AI",
          applicationCategory: "SearchApplication",
          applicationSubCategory: "SearchEngine",
          browserRequirements: "Requires JavaScript, HTML5, CSS3.",
          countryOfOrigin: "France",
          description: "A search engine for the MOAW dataset",
          image: "/assets/fluentui-emoji-cat.svg",
          inLanguage: "en-US",
          isAccessibleForFree: true,
          learningResourceType: "workshop",
          license: "https://github.com/clemlesne/feedback-fountain/blob/main/LICENCE",
          name: "MOAW Search",
          releaseNotes: "https://github.com/clemlesne/feedback-fountain/releases",
          teaches: "Usage of Microsoft Azure, technology, artificial intelligence, network, cloud native skills.",
          typicalAgeRange: "16-",
          version: import.meta.env.VITE_VERSION,
          sourceOrganization: {
            "@type": "Organization",
            name: "Microsoft",
            url: "https://microsoft.com",
          },
          potentialAction: {
            "@type": "SearchAction",
            target: "/?q={search_term_string}",
          },
          maintainer: {
            "@type": "Person",
            email: "clemence@lesne.pro",
            name: "Clémence Lesne",
          },
          isPartOf: {
            "@type": "WebSite",
            name: "MOAW",
            url: "https://microsoft.github.io/moaw",
          },
        }),
      ]} />
      <SearchBar fetchFeedbacks={fetchFeedbacks} />
      <div className="results">
        {feedbacks && feedbacks.map((feedback) => (
          <Result
            key={feedback.id}
            feedback={feedback}
          />
        ))}
      </div>
      <footer className="footer">
        <span>
          {import.meta.env.VITE_VERSION} ({import.meta.env.MODE})
        </span>
        <a
          href="https://github.com/clemlesne/feedback-fountain"
          target="_blank"
          rel="noreferrer"
        >
          Source code is open, let&apos;s talk about it!
        </a>
      </footer>
    </>
  );
}

export default App;
