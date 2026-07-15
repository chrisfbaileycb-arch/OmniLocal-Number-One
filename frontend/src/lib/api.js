import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API });

// Command Center
export const getOverview = () => client.get("/overview").then((r) => r.data);

// Content Director
export const getPrompts = () => client.get("/content/prompts").then((r) => r.data);
export const postCopy = (transcript) => client.post("/content/copy", { transcript }).then((r) => r.data);
export const postCritic = (index) => client.post("/content/critic", { index }).then((r) => r.data);
export const publishAll = (assetId, caption) =>
  client.post("/content/publish-all", { assetId, caption }).then((r) => r.data);

// Quality Content Executioner (Ad Engine)
export const getReports = () => client.get("/executioner/reports").then((r) => r.data);
export const reconcile = () => client.post("/executioner/reconcile").then((r) => r.data);
export const resetLoop = () => client.post("/executioner/reset").then((r) => r.data);
export const getRecommendedPlan = () => client.get("/executioner/recommended-plan").then((r) => r.data);
export const getConnections = () => client.get("/connections").then((r) => r.data);
export const setConnection = (platform, connected) =>
  client.put("/connections", { platform, connected }).then((r) => r.data);
export const getPathways = () => client.get("/connections/pathways").then((r) => r.data);
export const oauthStart = (platform) =>
  client.get(`/connections/oauth/${platform}/start`).then((r) => r.data);
export const oauthCallback = (platform, code) =>
  client.post("/connections/oauth/callback", { platform, code }).then((r) => r.data);

// Quality Customer Maximizer (Rewards / Gamification)
export const getGames = () => client.get("/maximizer/games").then((r) => r.data);
export const setActiveGame = (gameId) => client.put("/maximizer/games/active", { gameId }).then((r) => r.data);
export const getSegments = () => client.get("/maximizer/segments").then((r) => r.data);
export const getDrip = () => client.get("/maximizer/drip").then((r) => r.data);
export const spin = (isNewGuest, segment = "new") =>
  client.post("/maximizer/spin", { isNewGuest, segment }).then((r) => r.data);
export const getSampleCustomerCsv = () => client.get("/maximizer/sample-customer-csv").then((r) => r.data);
export const importCustomerCsv = (csv) => client.post("/maximizer/import-csv", { csv }).then((r) => r.data);
export const getWelcomeQueue = () => client.get("/maximizer/welcome-queue").then((r) => r.data);
export const sendWelcome = (index) => client.post("/email/send-welcome", { index }).then((r) => r.data);

// Codes & Redemption
export const getCurrentBatch = () => client.get("/codes/current").then((r) => r.data);
export const generateBatch = (length) => client.post("/codes/generate", { length }).then((r) => r.data);
export const getSampleCsv = () => client.get("/codes/sample-csv").then((r) => r.data);
export const reconcileCsv = (csv) => client.post("/codes/reconcile", { csv }).then((r) => r.data);

// Email Engine (Anti-Spam Trickle)
export const getTricklePlan = () => client.get("/email/trickle-plan?total=3000").then((r) => r.data);
export const previewEmail = (content) => client.post("/email/preview", { content }).then((r) => r.data);
