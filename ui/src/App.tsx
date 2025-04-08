"use client";

import type React from "react";
import { useState, useEffect, useRef } from "react";
import MarkdownRenderer from "./components/MarkdownRenderer";
import { Send, Loader2, RefreshCw, Settings, X, Check } from "lucide-react";

// Message types
type MessageType = "user" | "agent";

interface Message {
  type: MessageType;
  content: string;
  agentName?: string;
  timestamp: string;
}

interface Neo4jConfig {
  url: string;
  username: string;
  password: string;
  index_name: string;
}

interface Agent {
  address: string;
  name: string;
}

// Predefined GraphRag modes
const GRAPHRAG_MODES = [
  "GraphRag Entity-Focused Assistant",
  "GraphRag Global Assistant",
];

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConfig, setShowConfig] = useState(true);
  const [neo4jConfig, setNeo4jConfig] = useState<Neo4jConfig>({
    url: "",
    username: "neo4j",
    password: "",
    index_name: "entity",
  });

  const [selectedMode, setSelectedMode] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isSearchingAgent, setIsSearchingAgent] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<number | null>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load saved config from localStorage
  useEffect(() => {
    const savedConfig = localStorage.getItem("neo4jConfig");
    const savedAgent = localStorage.getItem("selectedAgent");
    const savedMode = localStorage.getItem("selectedMode");

    if (savedConfig) {
      setNeo4jConfig(JSON.parse(savedConfig));
    }

    if (savedAgent) {
      setSelectedAgent(JSON.parse(savedAgent));
      setShowConfig(false);
    }

    if (savedMode) {
      setSelectedMode(savedMode);
    }
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Search for agent address when a mode is selected
  const searchAgentAddress = async (modeName: string) => {
    setIsSearchingAgent(true);
    setError(null);

    try {
      const response = await fetch(
        `http://localhost:5005/api/search-agents?query=${encodeURIComponent(
          modeName
        )}`
      );

      if (response.ok) {
        const agents = await response.json();

        // Find the exact match for the mode name
        const matchedAgent = agents.find(
          (agent: Agent) => agent.name === modeName
        );

        if (matchedAgent) {
          setSelectedAgent(matchedAgent);
          localStorage.setItem("selectedAgent", JSON.stringify(matchedAgent));
          return true;
        } else if (agents.length > 0) {
          // If no exact match, use the first result
          setSelectedAgent(agents[0]);
          localStorage.setItem("selectedAgent", JSON.stringify(agents[0]));
          return true;
        } else {
          setError(`No agent found for ${modeName}`);
          return false;
        }
      } else {
        setError("Failed to search for agent");
        return false;
      }
    } catch (err) {
      setError("Error searching for agent");
      console.error(err);
      return false;
    } finally {
      setIsSearchingAgent(false);
    }
  };

  const selectMode = async (modeName: string) => {
    setSelectedMode(modeName);
    localStorage.setItem("selectedMode", modeName);

    // Search for the agent address
    await searchAgentAddress(modeName);
  };

  const saveConfig = () => {
    localStorage.setItem("neo4jConfig", JSON.stringify(neo4jConfig));
    setShowConfig(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing || !selectedAgent) return;

    // Add user message to chat
    const userMessage: Message = {
      type: "user",
      content: input,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsProcessing(true);
    setError(null);

    try {
      // Send message to API with Neo4j config and agent address as separate keys
      await fetch("http://localhost:5005/api/send-data", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          payload: {
            input: input,
            db_config: neo4jConfig,
          },
          agentAddress: selectedAgent.address,
        }),
      });
    } catch (err) {
      handleError(err);
      return;
    }

    // Start polling for response
    getResponse();
  };

  const getResponse = async () => {
    let attempts = 0;
    const maxAttempts = 30; // Maximum number of polling attempts
    const pollInterval = 1000; // Poll every 1 second

    // Clear any existing polling interval
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    // Create a polling function
    const pollForResponse = () => {
      pollIntervalRef.current = window.setInterval(async () => {
        try {
          attempts++;
          console.log(`Polling attempt ${attempts}`);

          const response = await fetch(
            "http://localhost:5005/api/get-response"
          );

          if (response.status === 200) {
            const data = await response.json();

            // Check if we have the output data
            if (data && data.output) {
              // Clear the polling interval as we got the data
              clearInterval(pollIntervalRef.current as number);
              pollIntervalRef.current = null;
              setIsProcessing(false);

              // Process agent responses
              setMessages((prev) => [
                ...prev,
                {
                  type: "agent",
                  agentName: data.source || "GraphRag Assistant",
                  content: data.output,
                  timestamp: new Date().toLocaleTimeString(),
                },
              ]);
            } else {
              console.log("No output data yet, continuing to poll...");
            }
          }

          // Stop polling after maximum attempts
          if (attempts >= maxAttempts) {
            clearInterval(pollIntervalRef.current as number);
            pollIntervalRef.current = null;
            setIsProcessing(false);
            setError("Response timed out. Please try again.");
          }
        } catch (error) {
          handleError(error);

          // Stop polling on error
          clearInterval(pollIntervalRef.current as number);
          pollIntervalRef.current = null;
        }
      }, pollInterval);
    };

    // Start polling
    pollForResponse();
  };

  const handleError = (error: any) => {
    console.error("Error:", error);
    setError("Something went wrong. Please try again.");
    setIsProcessing(false);
  };

  const retryLastMessage = () => {
    // Find the last user message
    const lastUserMessage = [...messages]
      .reverse()
      .find((msg) => msg.type === "user");
    if (lastUserMessage) {
      setInput(lastUserMessage.content);
    }
  };

  const openConfig = () => {
    setShowConfig(true);
  };

  useEffect(() => {
    return () => {
      // Clear any active polling intervals when component unmounts
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  return (
    <div className="flex flex-col h-screen bg-[#0A1128] text-[#F5F5F7]">
      {/* Header */}
      <header className="bg-[#121B30] p-4 border-b border-[#00E5FF]/20">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold bg-gradient-to-r from-[#7B42F6] to-[#00E5FF] bg-clip-text text-transparent">
            GraphRag Neo4j Assistant
          </h1>
          <div className="flex items-center space-x-2">
            {selectedAgent && (
              <span className="text-sm text-[#B8B8D1] mr-2">
                {selectedAgent.name}
              </span>
            )}
            <button
              onClick={openConfig}
              className="p-2 rounded-full hover:bg-[#1A2540] transition-colors"
              title="Settings"
            >
              <Settings className="h-5 w-5 text-[#00E5FF]" />
            </button>
          </div>
        </div>
      </header>

      {/* Configuration Modal */}
      {showConfig && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-[#121B30] rounded-lg border border-[#00E5FF]/20 w-full max-w-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-[#00E5FF]">
                Configuration
              </h2>
              <button
                onClick={() => selectedAgent && setShowConfig(false)}
                className="p-1 rounded-full hover:bg-[#1A2540]"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <h3 className="font-medium text-[#F5F5F7]">Neo4j Connection</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-[#B8B8D1] mb-1">
                    URL
                  </label>
                  <input
                    type="text"
                    value={neo4jConfig.url}
                    onChange={(e) =>
                      setNeo4jConfig({ ...neo4jConfig, url: e.target.value })
                    }
                    placeholder="bolt://localhost:7687"
                    className="w-full bg-[#0A1128] text-[#F5F5F7] rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#00E5FF]/50 border border-[#00E5FF]/20"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#B8B8D1] mb-1">
                    Username
                  </label>
                  <input
                    type="text"
                    value={neo4jConfig.username}
                    onChange={(e) =>
                      setNeo4jConfig({
                        ...neo4jConfig,
                        username: e.target.value,
                      })
                    }
                    placeholder="neo4j"
                    className="w-full bg-[#0A1128] text-[#F5F5F7] rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#00E5FF]/50 border border-[#00E5FF]/20"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#B8B8D1] mb-1">
                    Password
                  </label>
                  <input
                    type="password"
                    value={neo4jConfig.password}
                    onChange={(e) =>
                      setNeo4jConfig({
                        ...neo4jConfig,
                        password: e.target.value,
                      })
                    }
                    placeholder="Password"
                    className="w-full bg-[#0A1128] text-[#F5F5F7] rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#00E5FF]/50 border border-[#00E5FF]/20"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#B8B8D1] mb-1">
                    Index Name
                  </label>
                  <input
                    type="text"
                    value={neo4jConfig.index_name}
                    onChange={(e) =>
                      setNeo4jConfig({
                        ...neo4jConfig,
                        index_name: e.target.value,
                      })
                    }
                    placeholder="vector"
                    className="w-full bg-[#0A1128] text-[#F5F5F7] rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#00E5FF]/50 border border-[#00E5FF]/20"
                  />
                </div>
              </div>

              <div className="pt-2">
                <h3 className="font-medium text-[#F5F5F7] mb-2">
                  Select Assistant Mode
                </h3>

                <div className="space-y-2 bg-[#0A1128] rounded border border-[#00E5FF]/20 p-3">
                  {GRAPHRAG_MODES.map((mode) => (
                    <div key={mode} className="flex items-center">
                      <input
                        type="radio"
                        id={mode}
                        name="mode"
                        checked={selectedMode === mode}
                        onChange={() => selectMode(mode)}
                        className="hidden"
                      />
                      <label
                        htmlFor={mode}
                        className={`flex items-center justify-between w-full p-2 rounded cursor-pointer ${
                          selectedMode === mode
                            ? "bg-[#00E5FF]/10 text-[#00E5FF]"
                            : "hover:bg-[#1A2540] text-[#F5F5F7]"
                        }`}
                      >
                        <span>{mode}</span>
                        {selectedMode === mode &&
                          (isSearchingAgent ? (
                            <Loader2 className="h-4 w-4 text-[#00E5FF] animate-spin" />
                          ) : (
                            <Check className="h-4 w-4 text-[#00E5FF]" />
                          ))}
                      </label>
                    </div>
                  ))}
                </div>

                {selectedAgent && (
                  <div className="mt-2 text-xs text-[#00E5FF]">
                    Agent address: {selectedAgent.address.substring(0, 15)}...
                  </div>
                )}

                <div className="mt-2 text-xs text-[#B8B8D1]">
                  <p>
                    <strong>Entity-Focused:</strong> Focuses on specific
                    entities and their relationships
                  </p>
                  <p>
                    <strong>Global:</strong> Provides broader context and
                    general knowledge
                  </p>
                </div>

                {error && (
                  <div className="mt-2 text-xs text-red-400 bg-red-900/20 p-2 rounded border border-red-800">
                    {error}
                  </div>
                )}
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  onClick={saveConfig}
                  disabled={
                    !neo4jConfig.url ||
                    !neo4jConfig.password ||
                    !selectedAgent ||
                    isSearchingAgent
                  }
                  className={`px-4 py-2 rounded ${
                    !neo4jConfig.url ||
                    !neo4jConfig.password ||
                    !selectedAgent ||
                    isSearchingAgent
                      ? "bg-[#1A2540] text-[#B8B8D1] cursor-not-allowed"
                      : "bg-gradient-to-r from-[#7B42F6] to-[#00E5FF] text-white hover:opacity-90 transition-opacity"
                  }`}
                >
                  {isSearchingAgent ? (
                    <>
                      <Loader2 className="h-4 w-4 inline mr-2 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    "Save Configuration"
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Messages Container */}
      <div className="flex-1  p-4  space-y-4 max-w-7xl mx-auto w-full">
        {messages.length === 0 && !showConfig && (
          <div className="flex flex-col items-center justify-center h-full text-[#B8B8D1]">
            <div className="w-16 h-16 mb-4 rounded-full bg-gradient-to-r from-[#7B42F6] to-[#00E5FF] flex items-center justify-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-8 w-8 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <p className="text-center">
              Ask me anything using the GraphRag {selectedAgent?.name}!
            </p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.type === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-2xl p-4 ${
                message.type === "user"
                  ? "bg-[#7B42F6] text-white"
                  : "bg-[#121B30] border border-[#00E5FF]/20"
              }`}
            >
              <div className="whitespace-pre-wrap prose prose-sm max-w-none">
                {message.type === "agent" ? (
                  <MarkdownRenderer content={message.content} />
                ) : (
                  message.content
                )}
              </div>

              <div className="text-xs text-[#B8B8D1] mt-2 text-right">
                {message.timestamp}
              </div>
            </div>
          </div>
        ))}

        {isProcessing && (
          <div className="flex justify-start">
            <div className="bg-[#121B30] rounded-2xl p-4 border border-[#00E5FF]/20 max-w-[80%]">
              <div className="flex items-center space-x-2">
                <Loader2 className="h-4 w-4 text-[#00E5FF] animate-spin" />
                <span className="text-[#B8B8D1]">Processing your query...</span>
              </div>
            </div>
          </div>
        )}

        {error && !showConfig && (
          <div className="flex justify-center">
            <div className="bg-red-900/20 text-red-400 rounded-2xl p-4 border border-red-800 max-w-[80%] flex items-center">
              <span>{error}</span>
              <button
                onClick={retryLastMessage}
                className="ml-2 p-1 rounded-full hover:bg-red-800/30"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-[#121B30] border-t border-[#00E5FF]/20">
        <form
          onSubmit={handleSubmit}
          className="flex items-center space-x-2 max-w-3xl mx-auto"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isProcessing || !selectedAgent}
            placeholder={
              selectedAgent
                ? "Ask a question..."
                : "Configure Neo4j and select an assistant mode first"
            }
            className="flex-1 bg-[#0A1128] text-[#F5F5F7] rounded-full px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#00E5FF]/50 border border-[#00E5FF]/20"
          />
          <button
            type="submit"
            disabled={isProcessing || !input.trim() || !selectedAgent}
            className={`rounded-full p-3 ${
              isProcessing || !input.trim() || !selectedAgent
                ? "bg-[#121B30] text-[#B8B8D1] cursor-not-allowed"
                : "bg-[#7B42F6] text-white hover:opacity-90 transition-opacity"
            }`}
          >
            {isProcessing ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
