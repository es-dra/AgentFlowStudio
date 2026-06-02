export const ARTIFACT_REGISTRY = {
  agentflow_production_memory_asset_profile_seed: {
    aliases: ["production_memory_asset_profile_seed.example.json", "asset_profile_seed.json"],
    sourceRole: "production memory asset profile seed",
    label: "Production memory asset profile seed",
    workspaceSlot: "productionMemoryAssetProfileSeed",
    focusTargets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetProfileSeedFacts",
  },
  agentflow_production_memory_asset_profile: {
    aliases: ["asset_profile.json"],
    sourceRole: "production memory asset profile",
    label: "Production memory asset profile",
    workspaceSlot: "productionMemoryAssetProfile",
    focusTargets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetProfileFacts",
  },
  agentflow_production_memory_asset_profile_readiness: {
    aliases: ["asset_profile_readiness.json"],
    sourceRole: "production memory asset profile readiness",
    label: "Production memory asset profile readiness",
    workspaceSlot: "productionMemoryAssetProfileReadiness",
    focusTargets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetProfileReadinessFacts",
  },
  agentflow_production_memory_asset_test_package: {
    aliases: ["asset_test_package.json"],
    sourceRole: "production memory asset test package",
    label: "Production memory asset test package",
    workspaceSlot: "productionMemoryAssetTestPackage",
    focusTargets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetTestPackageFacts",
  },
  agentflow_production_memory_asset_provider_validation_plan: {
    aliases: ["provider_validation_plan.json"],
    sourceRole: "production memory asset provider validation plan",
    label: "Production memory asset provider validation plan",
    workspaceSlot: "productionMemoryAssetProviderValidationPlan",
    focusTargets: ["project", "assets", "review"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetProviderValidationFacts",
  },
  agentflow_production_memory_asset_provider_validation_blockers: {
    aliases: ["provider_validation_blockers.json"],
    sourceRole: "production memory asset provider validation blockers",
    label: "Production memory asset provider validation blockers",
    workspaceSlot: "productionMemoryAssetProviderValidationBlockers",
    focusTargets: ["project", "assets", "review"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetProviderValidationFacts",
  },
  agentflow_production_memory_asset_provider_validation_result: {
    aliases: ["provider_validation_result.json"],
    sourceRole: "production memory asset provider validation result",
    label: "Production memory asset provider validation result",
    workspaceSlot: "productionMemoryAssetProviderValidationResult",
    focusTargets: ["project", "assets", "review"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetProviderValidationFacts",
  },
  agentflow_production_memory_asset_feedback_event: {
    aliases: ["asset_feedback_event.json"],
    sourceRole: "production memory asset feedback event",
    label: "Production memory asset feedback",
    workspaceSlot: "productionMemoryAssetFeedbackEvent",
    focusTargets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetFeedbackFacts",
  },
  agentflow_production_memory_asset_profile_update_candidate: {
    aliases: ["asset_profile_update_candidate.json"],
    sourceRole: "production memory asset profile update candidate",
    label: "Production memory asset profile update candidate",
    workspaceSlot: "productionMemoryAssetProfileUpdateCandidate",
    focusTargets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetProfileUpdateCandidateFacts",
  },
  agentflow_production_memory_asset_profile_promotion_decision: {
    aliases: ["asset_profile_promotion_decision.json"],
    sourceRole: "production memory asset profile promotion decision",
    label: "Production memory asset profile promotion decision",
    workspaceSlot: "productionMemoryAssetProfilePromotionDecision",
    focusTargets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetProfilePromotionFacts",
  },
  agentflow_production_memory_asset_profile_version: {
    aliases: ["asset_profile_version.json"],
    sourceRole: "production memory asset profile version",
    label: "Production memory asset profile version",
    workspaceSlot: "productionMemoryAssetProfileVersion",
    focusTargets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetProfileVersionFacts",
  },
  agentflow_production_memory_asset_profile_context_projection: {
    aliases: ["asset_profile_context_projection.json"],
    sourceRole: "production memory asset profile context projection",
    label: "Production memory asset profile context projection",
    workspaceSlot: "productionMemoryAssetProfileContextProjection",
    focusTargets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetProfileContextProjectionFacts",
  },
  agentflow_production_memory_asset_consistency_review: {
    aliases: ["asset_consistency_review.json"],
    sourceRole: "production memory asset consistency review",
    label: "Production memory asset consistency review",
    workspaceSlot: "productionMemoryAssetConsistencyReview",
    focusTargets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
    viewRoute: "production_asset_cockpit",
    factsBuilder: "productionAssetConsistencyReviewFacts",
  },
};

export function artifactAliasesFromRegistry() {
  return Object.fromEntries(
    Object.entries(ARTIFACT_REGISTRY).map(([artifactType, definition]) => [artifactType, definition.aliases || []]),
  );
}

export function artifactSourceRoleFor(artifactType) {
  return ARTIFACT_REGISTRY[artifactType]?.sourceRole || "";
}

export function artifactLabelFor(artifactType) {
  return ARTIFACT_REGISTRY[artifactType]?.label || "";
}

export function artifactFocusTargetsFor(artifactType) {
  return [...(ARTIFACT_REGISTRY[artifactType]?.focusTargets || [])];
}

export function artifactWorkspaceSlotsFromRegistry(byType) {
  return Object.fromEntries(
    Object.entries(ARTIFACT_REGISTRY)
      .filter(([, definition]) => definition.workspaceSlot)
      .map(([artifactType, definition]) => [definition.workspaceSlot, byType(artifactType) || null]),
  );
}

export function artifactViewRouteFor(artifactType) {
  return ARTIFACT_REGISTRY[artifactType]?.viewRoute || "";
}
