from __future__ import annotations

import json
import subprocess
import textwrap


def _run_node(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
    )
    return json.loads(completed.stdout)


def test_asset_reuse_local_contract_models_states_explanations_and_reversal() -> None:
    payload = _run_node(
        textwrap.dedent(
            r'''
            import {
              assetReuseLocalContract,
              recordAssetReuseReversal,
            } from "./apps/studio/src/asset-reuse-contract.js";
            import { buildOptimizationRequest } from "./apps/studio/src/optimizer-contract.js";
            import { studioActionVocabularyEntry } from "./apps/studio/src/studio-entity-status-vocabulary.js";

            const longBase64Payload = "QUJD".repeat(40);
            const node = {
              id: "keyframe_1",
              type: "image",
              title: "Shot keyframe",
              prompt: "Generate a safe reviewable keyframe.",
              params: {
                nodeRole: "keyframe_generation",
                uploads: [
                  {
                    asset_id: "img_reference_1",
                    filename: "reference.png",
                    role: "reference_image",
                    reference_target: "keyframe_generation",
                    user_intent: `Use as pose ref while stripping raw_provider_response data_base64 data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA token=abc Bearer secret /home/owner/private.png C:\\private\\pose.png https://signed.example/private ${longBase64Payload}`,
                    media_kind: "image",
                    mime_type: "image/png",
                    preview_url: "https://signed.example/private",
                    data_base64: "QUJD",
                  },
                  {
                    asset_id: "img_asset_draft_1",
                    filename: "hero-draft.png",
                    role: "asset_reference",
                    reference_target: "asset_card_draft",
                    user_intent: "Draft only; not fixed.",
                    media_kind: "image",
                    mime_type: "image/png",
                  },
                ],
                visualAssets: [
                  {
                    asset_id: "fixed_hero_1",
                    label: "Hero",
                    asset_type: "character",
                    status: "fixed",
                    confidence: 0.91,
                    lock_state: "identity_locked",
                    source_node_id: "asset_card_hero",
                    source_evidence: {
                      source_contract: "fixed_asset_source_evidence",
                      source_human_gate_id: "gate_hero",
                      signed_url: "https://signed.example/hero",
                      raw_provider_response: { unsafe: true },
                      local_path: "/home/owner/private/hero.png",
                    },
                  },
                ],
                generationCandidates: [
                  {
                    candidate_id: "candidate_keyframe_1",
                    label: "Generated keyframe candidate",
                    status: "succeeded",
                    confidence: 0.88,
                    media_kind: "image",
                  },
                ],
                assetAutoBindingGraph: {
                  artifact_type: "agentflow_asset_auto_binding_graph",
                  algorithm_id: "afs.asset_auto_binding.v0.1",
                  binding_suggestions: [
                    {
                      binding_id: "binding:hero:fixed_hero_1",
                      binding_state: "bound",
                      graph_asset_id: "graph_hero",
                      fixed_visual_asset_id: "fixed_hero_1",
                      asset_type: "character",
                      label: "Hero",
                      confidence: 0.93,
                      lineage_refs: {
                        fixed_source_node_id: "asset_card_hero",
                        source_human_gate_id: "gate_hero",
                        source_asset_card_candidate_id: "asset_card_candidate_hero",
                      },
                    },
                  ],
                  blocked_candidates: [
                    {
                      graph_asset_id: "graph_scene",
                      asset_type: "scene",
                      label: "Town square",
                      confidence: 0.4,
                      block_reasons: ["low_confidence_candidate"],
                    },
                  ],
                },
                nodeReferenceStack: {
                  references: [
                    {
                      reference_type: "binding",
                      target_slot: "asset_binding:graph_prop",
                      target_ref: "fixed_prop_1",
                      conflict_state: "shadowed",
                      status: "bound",
                      source_algorithm_id: "afs.node_reference_stack.v0.1",
                    },
                  ],
                },
              },
            };
            const state = { nodes: { keyframe_1: node }, edges: {}, assets: [] };
            const before = assetReuseLocalContract(state, node);
            const candidate = before.items.find((item) => item.studio_entity_id === "generation_candidate");
            const reversalRecord = recordAssetReuseReversal(node, candidate);
            const after = assetReuseLocalContract(state, node);
            const optimization = buildOptimizationRequest(state, node);
            const actionChecks = before.items.map((item) => ({
              reuse_id: item.reuse_id,
              action: item.reversal.action,
              entity: item.reversal.studio_entity_id,
              applies: studioActionVocabularyEntry(item.reversal.action)?.appliesTo?.includes(item.reversal.studio_entity_id) || false,
            }));
            const nodePreservation = {
              upload_count: node.params.uploads.length,
              first_upload_asset_id: node.params.uploads[0].asset_id,
              generation_candidate_id: node.params.generationCandidates[0].candidate_id,
              visual_asset_id: node.params.visualAssets[0].asset_id,
            };
            process.stdout.write(JSON.stringify({ before, after, optimization, reversalRecord, nodePreservation, actionChecks }));
            '''
        )
    )

    before = payload["before"]
    states = {item["state"] for item in before["items"]}
    assert {"recognized", "reused", "graph-bound", "blocked", "conflicted"} <= states
    assert before["safety_boundary"]["provider_raw_response_exposed"] is False
    assert before["safety_boundary"]["signed_url_exposed"] is False

    serialized = json.dumps(payload, ensure_ascii=False)
    forbidden_fragments = [
        "raw_provider_response",
        "signed.example",
        "data_base64",
        "data:image/png",
        "iVBORw0KGgoAAAANSUhEUgAAAAUA",
        "QUJDQUJDQUJDQUJDQUJD",
        "C:\\private",
        "/home/owner",
        "Bearer secret",
        "token=abc",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in serialized

    draft = next(item for item in before["items"] if item["asset"]["reference_target"] == "asset_card_draft")
    assert draft["state"] == "recognized"
    assert draft["draft_candidate"] is True
    assert draft["confirmed_fixed_asset"] is False
    assert draft["asset"]["role"] == "asset_reference"
    assert draft["target"]["slot"] == "asset_card_draft"

    graph_bound = next(item for item in before["items"] if item["state"] == "graph-bound")
    assert graph_bound["source_evidence"]["source_algorithm_id"] == "afs.asset_auto_binding.v0.1"
    assert graph_bound["selected_state"] == "selected"
    assert graph_bound["reversal"]["action"] == "unbind"
    assert graph_bound["explanation_summary"].startswith("graph-bound: Hero -> keyframe_1/")

    upload_contract = next(item for item in before["items"] if item["target"]["slot"] == "keyframe_generation")
    assert upload_contract["source_evidence"]["user_intent"].startswith("Use as pose ref")
    uploaded_images = payload["optimization"]["node_parameters"]["uploaded_images"]
    assert uploaded_images[0]["user_intent"].startswith("Use as pose ref")

    candidate = next(item for item in before["items"] if item["studio_entity_id"] == "generation_candidate")
    assert candidate["reversal"]["action"] == "reject"
    assert payload["reversalRecord"]["deletes_asset"] is False
    assert payload["reversalRecord"]["deletes_candidate_record"] is False
    assert payload["nodePreservation"]["generation_candidate_id"] == "candidate_keyframe_1"
    assert payload["nodePreservation"]["first_upload_asset_id"] == "img_reference_1"
    assert payload["nodePreservation"]["upload_count"] == 2

    after_candidate = next(item for item in payload["after"]["items"] if item["studio_entity_id"] == "generation_candidate")
    assert after_candidate["state"] == "reversed/unbound"
    assert after_candidate["selected_state"] == "reversed"
    assert after_candidate["reversal"]["applied"] is True

    assert all(item["applies"] for item in payload["actionChecks"])
    asset_reuse = payload["optimization"]["node_parameters"]["asset_reuse"]
    assert asset_reuse["summary"]["graph_bound_count"] == 1
    assert "not human acceptance" in asset_reuse["non_claims"]


def test_storyboard_graph_bound_asset_flows_to_asset_cards_keyframes_and_contract() -> None:
    payload = _run_node(
        textwrap.dedent(
            r'''
            import { splitTextNodeToStoryboardNodes } from "./apps/studio/src/script-breakdown.js";
            import { ensureShotAssetPrepNodesForScriptNode } from "./apps/studio/src/shot-asset-nodes.js";
            import { createKeyframeNodesForStoryboard } from "./apps/studio/src/storyboard-keyframes.js";
            import { assetReuseLocalContract } from "./apps/studio/src/asset-reuse-contract.js";

            const graph = {
              artifact_type: "agentflow_asset_auto_binding_graph",
              schema_version: "0.1.0",
              algorithm_id: "afs.asset_auto_binding.v0.1",
              summary: { suggested_binding_count: 1, established_binding_count: 1, blocked_candidate_count: 0 },
              binding_suggestions: [{
                binding_id: "binding:graph_prop_map:fixed_map_1",
                binding_state: "bound",
                graph_asset_id: "graph:prop:地图",
                fixed_visual_asset_id: "fixed_map_1",
                asset_type: "prop",
                label: "地图",
                confidence: 0.92,
                lineage_refs: {
                  candidate_graph_asset_id: "graph:prop:地图",
                  fixed_visual_asset_id: "fixed_map_1",
                  fixed_source_node_id: "asset_card_map",
                  source_human_gate_id: "gate_map",
                  source_asset_card_candidate_id: "asset_card_candidate_map",
                },
                reversal_plan: { reversible: true, action: "unbind", preserve_lineage: true, destructive_asset_write: false },
              }],
              relationships: [{
                relationship_type: "asset_auto_binding_established",
                from_node_id: "asset:graph:prop:地图",
                to_node_id: "fixed_asset:fixed_map_1",
                binding_id: "binding:graph_prop_map:fixed_map_1",
                binding_state: "bound",
                confidence: 0.92,
                source: "afs.asset_auto_binding.v0.1",
              }],
              blocked_candidates: [],
              writes_long_term_memory: false,
              writes_company_kb: false,
            };

            const state = {
              nodes: {
                text_1: {
                  id: "text_1",
                  type: "text",
                  title: "Script",
                  x: 0,
                  y: 0,
                  w: 280,
                  h: 280,
                  prompt: "林晚检查地图。",
                  content: "林晚检查地图。",
                  params: {},
                  status: "complete",
                },
              },
              edges: {},
              order: ["text_1"],
              selection: { nodeIds: [], edgeId: null },
              ui: {},
              assets: [],
            };
            let seq = 0;
            const store = {
              get: () => state,
              nextId: () => `node_${++seq}`,
              set: (mutator) => mutator(state),
            };
            const runtime = {
              breakdownStoryboard: async () => ({
                safe_manifest: { status: "runtime_storyboard_breakdown" },
                provider_calls_started: false,
                shots: [{
                  shot_id: "shot_01",
                  index: 1,
                  duration: "5s",
                  description: "林晚检查地图。",
                  shot_size: "近景",
                  light_atmosphere: "冷色室内光",
                  camera_motion: "固定机位",
                  asset_refs: [{
                    label: "地图",
                    asset_type: "prop",
                    asset_id: "candidate:prop:map",
                    graph_asset_id: "graph:prop:地图",
                    status: "candidate",
                    source: "runtime",
                  }],
                }],
                asset_auto_binding_graph: graph,
                production_graph: {
                  artifact_type: "agentflow_production_graph_snapshot",
                  summary: { fixed_visual_asset_count: 1 },
                  nodes: [{ node_type: "fixed_visual_asset", asset_id: "fixed_map_1" }],
                },
                artifacts: {
                  asset_auto_binding_graph: { artifact_id: "artifact_binding_graph" },
                  production_graph_snapshot: { artifact_id: "artifact_production_graph" },
                },
              }),
            };

            const [shotId] = await splitTextNodeToStoryboardNodes(store, state.nodes.text_1, runtime);
            const shot = state.nodes[shotId];
            const [assetNodeId] = ensureShotAssetPrepNodesForScriptNode(store, shot, { replaceExisting: true });
            const assetNode = state.nodes[assetNodeId];
            const [keyframeId] = createKeyframeNodesForStoryboard(store, shot);
            const keyframe = state.nodes[keyframeId];
            const shotReuse = assetReuseLocalContract(state, shot);
            const assetReuse = assetReuseLocalContract(state, assetNode);

            process.stdout.write(JSON.stringify({
              sourceBreakdown: state.nodes.text_1.params.storyboardBreakdown,
              shot,
              assetNode,
              keyframe,
              shotReuse,
              assetReuse,
            }));
            '''
        )
    )

    source_breakdown = payload["sourceBreakdown"]
    shot_params = payload["shot"]["params"]
    asset_params = payload["assetNode"]["params"]
    keyframe_params = payload["keyframe"]["params"]

    assert source_breakdown["assetAutoBindingGraphArtifactId"] == "artifact_binding_graph"
    assert source_breakdown["assetAutoBindingGraph"]["summary"]["established_binding_count"] == 1
    assert shot_params["structuredShot"]["asset_refs"][0]["graph_asset_id"] == "graph:prop:地图"
    assert shot_params["nodeReferenceStack"]["summary"]["asset_auto_binding_reference_count"] == 1
    assert asset_params["nodeReferenceStack"]["references"][0]["target_ref"] == "fixed_map_1"
    assert keyframe_params["visualAssets"][0]["asset_id"] == "fixed_map_1"
    assert keyframe_params["keyframeLayer"]["fixed_visual_asset_ids"] == ["fixed_map_1"]
    assert payload["shotReuse"]["summary"]["graph_bound_count"] == 1
    assert payload["assetReuse"]["summary"]["graph_bound_count"] == 1
