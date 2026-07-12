import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API });

export const getOverview = () => client.get("/overview").then((r) => r.data);
export const getPrompts = () => client.get("/content/prompts").then((r) => r.data);
export const postCopy = (transcript) =>
  client.post("/content/copy", { transcript }).then((r) => r.data);
export const postCritic = (index) =>
  client.post("/content/critic", { index }).then((r) => r.data);
export const getReports = () => client.get("/adsmith/reports").then((r) => r.data);
export const reconcile = () => client.post("/adsmith/reconcile").then((r) => r.data);
export const resetLoop = () => client.post("/adsmith/reset").then((r) => r.data);
export const getSegments = () => client.get("/echolink/segments").then((r) => r.data);
export const getDrip = () => client.get("/echolink/drip").then((r) => r.data);
export const spin = (isNewGuest, segment = "new") =>
  client.post("/echolink/spin", { isNewGuest, segment }).then((r) => r.data);
