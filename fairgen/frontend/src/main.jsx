import React from "react";
import ReactDOM from "react-dom/client";
import { GoogleOAuthProvider } from "@react-oauth/google";
import App from "./pages/App";
import "./styles.css";

// GoogleOAuthProvider requires a clientId and will throw with an empty string.
// Use a placeholder when not configured — the login button is hidden in that case.
const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "__placeholder__";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={clientId}>
      <App />
    </GoogleOAuthProvider>
  </React.StrictMode>,
);
