from __future__ import annotations

from studio_static_helpers import STUDIO_ROOT


def test_agent_chat_panel_uses_runtime_llm_for_non_command_conversation() -> None:
    panel = (STUDIO_ROOT / "src" / "agent-chat-panel.js").read_text(encoding="utf-8")
    lifecycle = (STUDIO_ROOT / "src" / "agent-chat-lifecycle.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    service = (STUDIO_ROOT.parents[1] / "apps" / "api" / "runtime_service.py").read_text(encoding="utf-8")
    route = (STUDIO_ROOT.parents[1] / "apps" / "api" / "runtime_agent_chat_conversation.py").read_text(encoding="utf-8")

    assert "submitAgentChatMessageWithRuntime" in panel
    assert "runtime.agentChatConversation" in lifecycle
    assert "/agent-chat/conversation" in runtime_client
    assert "register_runtime_agent_chat_conversation_routes" in service
    assert "AGENT_CHAT_CONTRACT_ID" in route
    assert "SERVER_CODEX_SERVICE_ID" in route
    assert "structured_output_schema_digest" in route
    assert "AI 模型当前不可用，我不会用本地固定回答冒充理解" in lifecycle
    assert "conversationalReply(commandText, context)" not in panel


def test_agent_chat_runtime_conversation_keeps_command_preview_separate() -> None:
    lifecycle = (STUDIO_ROOT / "src" / "agent-chat-lifecycle.js").read_text(encoding="utf-8")

    assert "const command = previewAgentCommand(commandText, context);" in lifecycle
    assert 'if (command.command_type !== "none")' in lifecycle
    assert "return submitAgentChatMessage(session, rawText, context);" in lifecycle
    assert "agentChatRuntimeSummary" in lifecycle
    assert "graph_mutation" in lifecycle
