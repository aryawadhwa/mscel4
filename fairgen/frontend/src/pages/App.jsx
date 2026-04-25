import { useMemo, useRef, useState, useEffect } from "react";
import { ArrowRight, Check, CircleHelp, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useGoogleLogin } from "@react-oauth/google";

import AIPromptBox from "./components/AIPromptBox";
import ConfigPanel from "./components/ConfigPanel";
import DataTable from "./components/DataTable";
import DistributionCharts from "./components/DistributionCharts";
import DownloadPanel from "./components/DownloadPanel";
import FairnessReport from "./components/FairnessReport";
import SchemaBuilder from "./components/SchemaBuilder";
import ScoreHero from "./components/ScoreHero";
import Layout from "./components/Layout";
import PretextHero from "./components/PretextHero";
import Header from "./components/Header";
import Footer from "./components/Footer";
import VertexPanel from "./components/VertexPanel";
import { MotionWrapper, StaggerWrapper } from "./components/MotionWrapper";

import { generateDataset } from "./api/generate";
import { applyAIConstraint, suggestColumns, testApiConnection } from "./api/openai";
import { DEFAULT_CONFIG, DEFAULT_SCHEMA, DEMO_SCHEMA, FAIRNESS_BADGES, TABS, buildSchemaColumn } from "../config/constants";

const GENERATION_STEPS = [
  "Fitting SDV synthesizer...",
  "Sampling base records...",
  "Applying historical bias correction...",
  "Enforcing representation constraints...",
  "Correcting label bias...",
  "Injecting measurement noise parity...",
  "Computing fairness metrics...",
];

const DEMOGRAPHIC_COLUMNS = new Set([
  "age",
  "gender",
  "race",
  "zip_code_tier",
  "marital_status",
  "education_level",
  "dependents_count",
  "citizenship_status",
]);

const FINANCIAL_COLUMNS = new Set([
  "annual_income",
  "employment_status",
  "credit_score",
  "debt_to_income",
  "prior_defaults",
  "savings_balance",
  "monthly_expenses",
  "existing_loans",
  "assets_value",
]);

function fairnessTone(score) {
  if (score >= 80) {
    return {
      label: "Strong",
      chipClassName: "text-emerald-700 border-emerald-200 bg-emerald-50",
      accentClassName: "from-emerald-500 via-teal-400 to-cyan-400",
      message: "Strong structural integrity. Your dataset maintains fairness across protected groups.",
    };
  }
  if (score >= 60) {
    return {
      label: "Improving",
      chipClassName: "text-amber-700 border-amber-200 bg-amber-50",
      accentClassName: "from-amber-400 via-orange-300 to-yellow-300",
      message: "The structure is emerging. Some demographic gaps still require calibration.",
    };
  }
  return {
    label: "Critical",
    chipClassName: "text-rose-700 border-rose-200 bg-rose-50",
    accentClassName: "from-rose-400 via-orange-400 to-amber-400",
    message: "High entropy detected. Protected groups are facing significant disparate outcomes.",
  };
}

function serializeConfig(config) {
  return JSON.stringify(config);
}

function serializeSchema(schema) {
  return JSON.stringify(schema);
}

function getProgressFromStatus(statusMessage, loading) {
  if (!loading) {
    return 100;
  }
  const stepIndex = GENERATION_STEPS.indexOf(statusMessage);
  if (stepIndex === -1) {
    return 10;
  }
  return Math.round(((stepIndex + 1) / GENERATION_STEPS.length) * 100);
}

function removeSchemaColumnAt(schema, index) {
  return schema.filter((_, currentIndex) => currentIndex !== index);
}

function reorderSchema(schema, fromIndex, toIndex) {
  const next = [...schema];
  const [moved] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, moved);
  return next;
}

export default function App() {
  const [schema, setSchema] = useState(DEFAULT_SCHEMA);
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [step, setStep] = useState("schema");
  const [activeTab, setActiveTab] = useState("table");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Build a schema to get started");
  const [aiExplanation, setAiExplanation] = useState("");
  const [apiStatus, setApiStatus] = useState({ connected: false, message: "Not tested" });
  const [resumeReady, setResumeReady] = useState(false);
  const [persistState, setPersistState] = useState("");
  const [showGenerateSuccess, setShowGenerateSuccess] = useState(false);
  const [lastGeneratedConfig, setLastGeneratedConfig] = useState(DEFAULT_CONFIG);
  const [lastGeneratedSchema, setLastGeneratedSchema] = useState(DEFAULT_SCHEMA);
  const [schemaValidationError, setSchemaValidationError] = useState("");
  const [agePromptPending, setAgePromptPending] = useState(false);
  const [agePromptDismissed, setAgePromptDismissed] = useState(false);
  const [schemaSuggestions, setSchemaSuggestions] = useState([]);
  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const controllerRef = useRef(null);
  const fileInputRef = useRef(null);
  const lastRequestedConfigRef = useRef(DEFAULT_CONFIG);
  const successTimeoutRef = useRef(null);
  const [user, setUser] = useState(null);

  const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        const userInfo = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
        }).then(res => res.json());
        setUser(userInfo);
      } catch (error) {
        console.error("Failed to fetch user info:", error);
      }
    },
    onError: () => console.error("Login Failed"),
  });

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [step]);

  const score = result?.metrics?.OFS ?? 0;
  const scoreTone = fairnessTone(score);
  const statusProgress = getProgressFromStatus(statusMessage, loading);
  const configDirty = serializeConfig(config) !== serializeConfig(lastGeneratedConfig);
  const schemaDirty = serializeSchema(schema) !== serializeSchema(lastGeneratedSchema);
  const monitoredColumns = schema.filter((column) => column.fairness_sensitive);

  function triggerSuccessState() {
    setShowGenerateSuccess(true);
    if (successTimeoutRef.current) {
      window.clearTimeout(successTimeoutRef.current);
    }
    successTimeoutRef.current = window.setTimeout(() => setShowGenerateSuccess(false), 1800);
  }

  async function handleGenerate(nextConfig = config, nextSchema = schema) {
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    const controller = new AbortController();
    controllerRef.current = controller;
    lastRequestedConfigRef.current = nextConfig;
    setLoading(true);
    setResumeReady(false);
    setShowGenerateSuccess(false);
    setStatusMessage(GENERATION_STEPS[0]);
    try {
      const response = await generateDataset(nextSchema, nextConfig, (message) => setStatusMessage(message), controller.signal);
      setConfig(nextConfig);
      setSchema(nextSchema);
      setResult(response);
      setLastGeneratedConfig(nextConfig);
      setLastGeneratedSchema(nextSchema);
      setStatusMessage("Dataset ready. Check your Fairness Report.");
      triggerSuccessState();
    } catch (error) {
      if (error.name === "AbortError") {
        setStatusMessage("Generation paused");
        setResumeReady(true);
      } else {
        setStatusMessage(error.message || "Generation failed");
      }
    } finally {
      setLoading(false);
      controllerRef.current = null;
    }
  }

  async function handleApplyAIConstraint(instruction) {
    setLoading(true);
    setStatusMessage("Interpreting fairness instruction...");
    try {
      const response = await applyAIConstraint(instruction, config);
      const merged = {
        ...config,
        ...response.configDelta,
        representation: {
          ...config.representation,
          ...(response.configDelta.representation || {}),
        },
        measurementNoise: {
          ...config.measurementNoise,
          ...(response.configDelta.measurementNoise || {}),
        },
      };
      setAiExplanation(response.explanation);
      await handleGenerate(merged, schema);
    } catch (error) {
      setStatusMessage(error.message || "AI constraint failed");
      setLoading(false);
    }
  }

  async function handleApiTest() {
    setApiStatus({ connected: false, message: "Testing..." });
    try {
      const response = await testApiConnection();
      setApiStatus({
        connected: response.geminiConnected,
        message: response.geminiMessage || (response.geminiConnected ? "Connected" : "Connection failed"),
      });
    } catch (error) {
      setApiStatus({ connected: false, message: error.message || "Connection failed" });
    }
  }

  function handleConfigChange(partial) {
    setConfig((current) => ({
      ...current,
      ...partial,
      representation: {
        ...current.representation,
        ...(partial.representation || {}),
      },
      measurementNoise: {
        ...current.measurementNoise,
        ...(partial.measurementNoise || {}),
      },
    }));
  }

  function handleDemoScenario() {
    setSchema(DEMO_SCHEMA);
    setStep("config");
    setSchemaValidationError("");
    setAgePromptPending(false);
    setAgePromptDismissed(false);
    setAiExplanation("Loaded a ready-to-generate schema for a biased credit-risk demo scenario.");
  }

  function handleSaveConfig() {
    const payload = JSON.stringify({ config, schema }, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "de.bias-config.json";
    anchor.click();
    URL.revokeObjectURL(url);
    setPersistState("Config and schema saved as JSON");
    window.setTimeout(() => setPersistState(""), 2000);
  }

  function handleLoadConfigClick() {
    fileInputRef.current?.click();
  }

  async function handleLoadConfigFile(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      const contents = await file.text();
      const parsed = JSON.parse(contents);
      const mergedConfig = {
        ...DEFAULT_CONFIG,
        ...(parsed.config || parsed),
        representation: { ...DEFAULT_CONFIG.representation, ...((parsed.config || parsed).representation || {}) },
        measurementNoise: { ...DEFAULT_CONFIG.measurementNoise, ...((parsed.config || parsed).measurementNoise || {}) },
      };
      const loadedSchema = Array.isArray(parsed.schema) && parsed.schema.length ? parsed.schema : DEFAULT_SCHEMA;
      setConfig(mergedConfig);
      setSchema(loadedSchema);
      setStep("config");
      setPersistState("Config and schema loaded");
      window.setTimeout(() => setPersistState(""), 2000);
    } catch {
      setPersistState("Could not read that config file");
      window.setTimeout(() => setPersistState(""), 2500);
    } finally {
      event.target.value = "";
    }
  }

  function handleStopGeneration() {
    controllerRef.current?.abort();
  }

  function handleTogglePreset(name) {
    setSchemaValidationError("");
    setAgePromptPending(false);
    setSchemaSuggestions((current) => current.filter((suggestion) => suggestion.name !== name));
    setSchema((current) => {
      const exists = current.some((column) => column.name === name);
      if (exists) {
        return current.filter((column) => column.name !== name || column.name === "loan_approved");
      }
      return [...current, buildSchemaColumn(name)];
    });
  }

  function handleUpdateSchemaColumn(index, nextColumn) {
    setSchema((current) => current.map((column, currentIndex) => (currentIndex === index ? nextColumn : column)));
  }

  function handleRemoveSchemaColumn(index) {
    setSchema((current) => removeSchemaColumnAt(current, index));
  }

  function validateSchema(nextSchema) {
    const hasOutcome = nextSchema.some((column) => column.name === "loan_approved");
    const hasSensitiveDemographic = nextSchema.some((column) => column.fairness_sensitive && DEMOGRAPHIC_COLUMNS.has(column.name));
    const hasFinancial = nextSchema.some((column) => FINANCIAL_COLUMNS.has(column.name));
    const hasSensitive = nextSchema.some((column) => column.fairness_sensitive);

    if (!hasSensitiveDemographic || !hasFinancial || !hasOutcome) {
      return "Select at least one monitored demographic column, one financial column, and the required loan_approved outcome before continuing.";
    }
    if (!hasSensitive) {
      return "de.bias needs at least one protected attribute column (e.g. race, gender, age) to compute fairness metrics.";
    }
    return "";
  }

  function proceedToConfig(nextSchema = schema) {
    const validationMessage = validateSchema(nextSchema);
    if (validationMessage) {
      setSchemaValidationError(validationMessage);
      return;
    }

    const ageColumn = nextSchema.find((column) => column.name === "age");
    if (ageColumn && !ageColumn.fairness_sensitive && !agePromptDismissed) {
      setAgePromptPending(true);
      setSchemaValidationError("");
      return;
    }

    setSchemaValidationError("");
    setAgePromptPending(false);
    setStep("config");
    setStatusMessage("Schema ready. Tune your fairness controls.");
  }

  function handleEnableAgeMonitoring() {
    const nextSchema = schema.map((column) => (column.name === "age" ? { ...column, fairness_sensitive: true } : column));
    setSchema(nextSchema);
    setAgePromptPending(false);
    proceedToConfig(nextSchema);
  }

  function handleSkipAgeMonitoring() {
    setAgePromptDismissed(true);
    setAgePromptPending(false);
    proceedToConfig(schema);
  }

  async function handleSuggestColumns(description) {
    setSuggestionLoading(true);
    try {
      const response = await suggestColumns(
        description,
        schema.map((column) => column.name),
      );
      setSchemaSuggestions(response.suggestions || []);
    } catch (error) {
      setSchemaValidationError(error.message || "Could not fetch AI schema suggestions.");
    } finally {
      setSuggestionLoading(false);
    }
  }

  function handleAddSuggestion(suggestion) {
    setSchema((current) => {
      if (current.some((column) => column.name === suggestion.name)) {
        return current;
      }
      return [...current, suggestion];
    });
    setSchemaSuggestions((current) => current.filter((item) => item.name !== suggestion.name));
  }

  function handleAddAllSuggestions() {
    setSchema((current) => {
      const names = new Set(current.map((column) => column.name));
      const additions = schemaSuggestions.filter((suggestion) => !names.has(suggestion.name));
      return [...current, ...additions];
    });
    setSchemaSuggestions([]);
  }

  const tabs = useMemo(
    () => ({
      table: <DataTable rows={result?.dataset || []} schema={schema} />,
      charts: <DistributionCharts charts={result?.charts} />,
      report: <FairnessReport metrics={result?.metrics} fairnessReport={result?.fairnessReport} beforeMetrics={result?.beforeMetrics} geminiNarrative={result?.geminiNarrative} />,
    }),
    [result, schema],
  );

  const generateButtonLabel = loading
    ? "Generating dataset..."
    : showGenerateSuccess
      ? "Dataset generated"
      : result
        ? configDirty || schemaDirty
          ? "Regenerate with new settings"
          : "Generate dataset again"
        : "Generate dataset";

  return (
    <Layout>
      <Header 
        score={score}
        scoreTone={scoreTone}
        result={result}
        loading={loading}
        step={step}
        user={user}
        statusProgress={statusProgress}
        onEditSchema={() => setStep("schema")}
        onSetActiveTab={setActiveTab}
        onLogin={() => googleLogin()}
      />
      <div className="mx-auto max-w-7xl px-4 sm:px-6 pb-24 pt-24 sm:pt-32">
        <AnimatePresence>
          {step === "schema" && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            >
              <PretextHero />
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-8">
          <AnimatePresence mode="wait">
            {step === "schema" ? (
              <motion.div
                key="schema-step"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 1.02 }}
                transition={{ duration: 0.4 }}
              >
                <SchemaBuilder
                  schema={schema}
                  suggestions={schemaSuggestions}
                  suggestionLoading={suggestionLoading}
                  validationError={schemaValidationError}
                  agePromptPending={agePromptPending}
                  onTogglePreset={handleTogglePreset}
                  onUpdateColumn={handleUpdateSchemaColumn}
                  onRemoveColumn={handleRemoveSchemaColumn}
                  onReorder={(fromIndex, toIndex) => setSchema((current) => reorderSchema(current, fromIndex, toIndex))}
                  onSuggest={handleSuggestColumns}
                  onAddSuggestion={handleAddSuggestion}
                  onAddAllSuggestions={handleAddAllSuggestions}
                  onDismissSuggestions={() => setSchemaSuggestions([])}
                  onProceed={() => proceedToConfig(schema)}
                  onEnableAgeMonitoring={handleEnableAgeMonitoring}
                  onSkipAgeMonitoring={handleSkipAgeMonitoring}
                />
              </motion.div>
            ) : (
              <motion.div
                key="config-step"
                initial={{ opacity: 0, scale: 1.02 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                transition={{ duration: 0.4 }}
                className="grid gap-8 lg:grid-cols-[340px_minmax(0,1fr)] xl:grid-cols-[380px_minmax(0,1fr)]"
              >
                <div className="space-y-8">
                  <div className="rounded-2xl bg-gradient-to-br from-white/70 to-emerald-50/40 backdrop-blur-sm p-6 shadow-[0_4px_24px_rgba(0,100,100,0.22)]">
                    <ConfigPanel
                      config={config}
                      schema={schema}
                      onChange={handleConfigChange}
                      onGenerate={() => handleGenerate(config, schema)}
                      onReset={() => setConfig(DEFAULT_CONFIG)}
                      onSaveConfig={handleSaveConfig}
                      onLoadConfig={handleLoadConfigClick}
                      onEditSchema={() => setStep("schema")}
                      busy={loading}
                      generateLabel={generateButtonLabel}
                      showGenerateSuccess={showGenerateSuccess}
                    />
                  </div>
                  <AIPromptBox
                    apiStatus={apiStatus}
                    aiExplanation={aiExplanation}
                    onApply={handleApplyAIConstraint}
                    onTestConnection={handleApiTest}
                  />
                </div>

                <div className="space-y-12">
                  <AnimatePresence mode="wait">
                    {result && (
                      <ScoreHero 
                        key="score-hero"
                        score={score}
                        scoreTone={scoreTone}
                        onOpenReport={() => setActiveTab("report")}
                      />
                    )}
                  </AnimatePresence>

                  <div className="rounded-2xl bg-gradient-to-br from-white/70 to-emerald-50/40 backdrop-blur-sm p-6 shadow-[0_4px_24px_rgba(0,100,100,0.22)]">
                    <div className="mb-6 grid gap-3 grid-cols-1 sm:grid-cols-3">
                      {TABS.map((tab, index) => {
                        const active = activeTab === tab.id;
                        return (
                          <button
                            key={tab.id}
                            className={`flex items-center justify-between rounded-xl px-5 py-4 text-left transition active:scale-95 ${
                              active ? "bg-slate-900 text-white shadow-lg shadow-slate-900/20" : "bg-white/50 text-slate-500 hover:bg-white/70 shadow-[0_1px_8px_rgba(0,100,100,0.14)]"
                            }`}
                            onClick={() => setActiveTab(tab.id)}
                          >
                            <div>
                              <p className={`text-[10px] font-bold uppercase tracking-[0.2em] ${active ? "text-slate-400" : "text-slate-400"}`}>{`0${index + 1}`}</p>
                              <p className="mt-1 text-sm font-bold">{tab.label}</p>
                            </div>
                            <ArrowRight size={16} className={active ? "text-slate-400" : "text-slate-300"} />
                          </button>
                        );
                      })}
                    </div>

                    <div className="min-h-[500px]">
                      <AnimatePresence mode="wait">
                        <motion.div
                          key={activeTab}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -10 }}
                          transition={{ duration: 0.3 }}
                        >
                          {tabs[activeTab]}
                        </motion.div>
                      </AnimatePresence>
                    </div>
                  </div>

                  <DownloadPanel config={{ ...config, schema }} result={result} />

                  <VertexPanel result={result} schema={schema} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <AnimatePresence>
        {loading && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] flex items-center justify-center bg-white/60 px-4 backdrop-blur-lg"
          >
            <div className="w-full max-w-md rounded-[3rem] border border-white/50 bg-white/80 p-12 text-center shadow-2xl shadow-emerald-900/10">
              <div className="mx-auto mb-8 h-20 w-20 animate-spin rounded-full border-[6px] border-emerald-100 border-t-emerald-600" />
              <h2 className="text-3xl font-bold tracking-tight text-slate-900">{statusMessage}</h2>
              <div className="mt-8 h-4 overflow-hidden rounded-full bg-emerald-50 p-1">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${statusProgress}%` }}
                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-sky-500" 
                />
              </div>
              <p className="mt-8 text-sm font-medium text-slate-500 italic">Structural calibration in progress...</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <Footer 
        onLoadDemo={handleDemoScenario}
        onLogin={() => googleLogin()}
      />

      <input ref={fileInputRef} type="file" accept="application/json" className="hidden" onChange={handleLoadConfigFile} />
    </Layout>
  );
}
