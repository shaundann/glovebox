import React, { useEffect, useMemo, useState } from "react";
import { useConversation } from "@elevenlabs/react";

export default function GloveBox() {
  const [status, setStatus] = useState("idle");
  const [lastError, setLastError] = useState("");

  const conversation = useConversation({
    onConnect: () => {
      console.log("Connected successfully");
      setStatus("connected");
      setLastError("");
    },
    onDisconnect: (e) => {
      console.log("Disconnected event:", e);
      if (e) {
        console.log("Disconnect code:", e.code, "reason:", e.reason);
        console.log("Disconnect details:", JSON.stringify(e, null, 2));
      }
      // Only set to disconnected if we were actually connected
      // Don't override error status
      if (status !== "error") {
        setStatus("disconnected");
      }
    },
    onError: (e) => {
      console.error("ElevenLabs error:", e);

      // CloseEvent from WebSocket often has code/reason
      if (e && typeof e === "object" && "code" in e) {
        setLastError(`CloseEvent code=${e.code} reason=${e.reason || "(no reason)"}`);
      } else {
        setLastError(e?.message ?? JSON.stringify(e));
      }

      setStatus("error");
    },
    onMessage: (message) => {
      console.log("Received message:", message);
      console.log("Message type:", message?.type);
      console.log("Message content:", JSON.stringify(message, null, 2));
    },
    onUserSpeechStart: () => {
      console.log("User started speaking");
    },
    onUserSpeechEnd: () => {
      console.log("User stopped speaking");
    },
    onAgentSpeechStart: () => {
      console.log("Agent started speaking");
    },
    onAgentSpeechEnd: () => {
      console.log("Agent stopped speaking");
    },
    onAgentInterrupt: () => {
      console.log("Agent was interrupted");
    },
    onConversationUpdate: (update) => {
      console.log("Conversation update:", update);
    },
  });

  // Helpful: log available methods once so you can see what your SDK exposes
  useEffect(() => {
    console.log("conversation object:", conversation);
    if (conversation) {
      console.log("conversation keys:", Object.keys(conversation));
      // Log status if available
      if (conversation.status !== undefined) {
        console.log("conversation status:", conversation.status);
      }
      if (conversation.isConnected !== undefined) {
        console.log("conversation isConnected:", conversation.isConnected);
      }
    }
  }, [conversation, status]);

  // Pick the right start/stop method depending on the SDK version
  const startFn = useMemo(() => {
    return (
      conversation?.startSession ||
      conversation?.startConversation ||
      conversation?.connect ||
      conversation?.start
    );
  }, [conversation]);

  const stopFn = useMemo(() => {
    return (
      conversation?.endSession ||
      conversation?.stopSession ||
      conversation?.endConversation ||
      conversation?.disconnect ||
      conversation?.stop
    );
  }, [conversation]);

  async function start() {
    const backendUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
    const agentId = import.meta.env.VITE_ELEVENLABS_AGENT_ID;
    
    // Guard: do nothing if already connecting/connected
    if (status === "connecting" || status === "connected") return;

    try {
      setStatus("connecting");
      setLastError("");

      const fn =
        conversation?.startSession ||
        conversation?.startConversation ||
        conversation?.connect ||
        conversation?.start;

      if (!fn) throw new Error("No start method found on conversation object.");

      // Try to get a conversation token from the backend first
      // If that fails or isn't available, fall back to using agentId directly
      let connectionParams = {};
      
      try {
        console.log("Fetching conversation token from backend...");
        const tokenResponse = await fetch(`${backendUrl}/elevenlabs/token`);
        
        if (tokenResponse.ok) {
          const tokenData = await tokenResponse.json();
          console.log("Received token data:", tokenData);
          
          // The token might be in different fields depending on the API response
          const conversationToken = tokenData.conversation_token || tokenData.token || (typeof tokenData === 'string' ? tokenData : null);
          
          if (conversationToken) {
            console.log("Using conversation token for connection");
            // Try different parameter names the SDK might accept
            connectionParams = {
              conversationToken: conversationToken,
              token: conversationToken,
            };
          } else {
            console.warn("Token response didn't contain a valid token, falling back to agentId");
            if (agentId) {
              connectionParams = { agentId: agentId };
            } else {
              throw new Error("No agentId or token available");
            }
          }
        } else {
          console.warn("Failed to get token from backend, falling back to agentId");
          if (agentId) {
            connectionParams = { agentId: agentId };
          } else {
            throw new Error("Backend token endpoint failed and no agentId configured");
          }
        }
      } catch (tokenError) {
        console.warn("Error fetching token:", tokenError);
        // Fall back to agentId if available
        if (agentId) {
          console.log("Falling back to agentId:", agentId);
          connectionParams = { agentId: agentId };
        } else {
          throw new Error(`Failed to get token and no agentId configured: ${tokenError.message}`);
        }
      }

      console.log("Starting conversation with params:", connectionParams);
      await fn(connectionParams);

      console.log("Start function completed, waiting for onConnect callback");
      // NOTE: onConnect callback should set status to "connected"
    } catch (e) {
      console.error("Start failed:", e);

      const code = e?.code;
      const reason = e?.reason;
      if (typeof code === "number") {
        setLastError(`CloseEvent code=${code} reason=${reason || "(no reason)"}`);
      } else {
        setLastError(e?.message || JSON.stringify(e, Object.getOwnPropertyNames(e)));
      }

      setStatus("error");
    }
  }


  async function stop() {
    try {
      if (!stopFn) {
        console.error("No stop method found on conversation:", conversation);
        setStatus("error");
        setLastError("No stop method found on conversation object.");
        return;
      }
      await stopFn();
    } catch (e) {
      console.error("Stop failed:", e);
      setStatus("error");
      setLastError(e?.message ?? String(e));
    }
  }

  return (
    <div style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1 style={{ fontSize: 64, margin: "0 0 24px 0" }}>GloveBox</h1>

      <p style={{ fontSize: 22, margin: "0 0 18px 0" }}>
        Status: <strong>{status}</strong>
      </p>

      {lastError ? (
        <p style={{ marginTop: 0, marginBottom: 18 }}>
          <strong>Error:</strong> {lastError}
        </p>
      ) : null}

      <div style={{ display: "flex", gap: 12, marginBottom: 18 }}>
        <button
          onClick={start}
          disabled={status === "connecting" || status === "connected"}
          style={{
            padding: "12px 18px",
            borderRadius: 10,
            border: "1px solid #444",
            background: status === "connected" ? "#222" : "#111",
            color: "#fff",
            cursor: "pointer",
            opacity:
              status === "connecting" || status === "connected" ? 0.5 : 1,
          }}
        >
          Start Talking
        </button>

        <button
          onClick={stop}
          disabled={status !== "connected"}
          style={{
            padding: "12px 18px",
            borderRadius: 10,
            border: "1px solid #444",
            background: "#111",
            color: "#fff",
            cursor: "pointer",
            opacity: status !== "connected" ? 0.5 : 1,
          }}
        >
          Stop
        </button>
      </div>

      <p style={{ fontSize: 20, lineHeight: 1.5, maxWidth: 900 }}>
        Try saying: “Start a new session with 3 trials” or “Store 0.5 mL solvent
        for trial 1”.
      </p>

      <p style={{ fontSize: 14, opacity: 0.7, marginTop: 18 }}>
        Tip: Open DevTools Console to see the conversation object + available
        methods.
      </p>
    </div>
  );
}
