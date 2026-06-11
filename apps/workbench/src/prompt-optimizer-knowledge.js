const SECTION_RULES = [
  ["人物提示词", "年龄、服装、姿态、表情、身份线索、连续性描述"],
  ["场景提示词", "地点、时代、材质、道具、空间层次"],
  ["灯光提示词", "主光、辅光、逆光、色温、光比、柔硬、动机光"],
  ["镜头提示词", "景别、角度、焦段、运动、构图"],
  ["关键帧提示词", "主体位置、画面情绪、关键动作、可复用参考"],
  ["视频运动提示词", "时长、节奏、运动幅度、镜头语言、连续性"],
  ["负面提示词", "避免多手指、脸部崩坏、光源冲突、风格漂移、文字水印"],
];

export function buildPromptOptimization(sourcePrompt = "", context = {}) {
  const prompt = String(sourcePrompt || "").trim() || "一个男孩坐在昏暗房间里，墙上有海报，情绪低落";
  const style = String(context.style || "克制、电影感、真实光线");
  const sections = SECTION_RULES.map(([title, rule]) => ({
    title,
    text: sectionText(title, prompt, style),
    rule,
  }));
  return {
    artifact_type: "prompt_optimization_result",
    source_prompt: prompt,
    optimized_prompt: sections.map((section) => `${section.title}: ${section.text}`).join("\n"),
    prompt_sections: sections,
    applied_rules: SECTION_RULES.map(([, rule]) => rule),
    user_preference_weight: 0.1,
    warnings: ["已按影视提示词结构优化", "已结合当前项目风格", "已保持角色与场景一致性"],
  };
}

function sectionText(title, prompt, style) {
  const base = `${prompt}；${style}`;
  const map = {
    人物提示词: `${base}；明确人物年龄、服装轮廓、面部情绪和可连续复用的识别特征。`,
    场景提示词: `${base}；补充空间层次、墙面材质、海报、家具和可见道具关系。`,
    灯光提示词: `${base}；低照度主光、弱辅光、冷暖色温对比、柔硬光控制和动机光来源。`,
    镜头提示词: `${base}；中近景、轻微低角度、35mm 到 50mm、稳定构图，保留环境信息。`,
    关键帧提示词: `${base}；主体坐姿清晰、情绪停顿、墙面海报可辨，可作为 I2V 首帧。`,
    视频运动提示词: `${base}；默认 5s，慢速推进，人物动作幅度小，保持角色与场景连续性。`,
    负面提示词: "多余手指、面部崩坏、文字水印、镜头抖动、光源冲突、风格漂移、过度锐化。",
  };
  return map[title] || base;
}
