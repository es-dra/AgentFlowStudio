// 广场类延伸窗口的本地预置卡片数据。
// 封面用本地渐变占位，不引用外部图片资源。

export const MOTION_PRESETS = [
  "固定镜头", "跟随拍摄", "盘旋抬升", "盘旋下降",
  "镜头上摇", "镜头下摇", "镜头左摇", "镜头右摇",
  "推近", "拉远", "横移跟随", "弧形环绕",
  "升降镜头", "甩镜转场", "手持晃动", "希区柯克变焦",
].map((name, i) => ({
  id: `motion_${i + 1}`,
  name,
  hue: (i * 37) % 360,
  meta: "运镜",
}));

export const STYLE_PRESETS = [
  ["城市巨人", "摄影写真"], ["巨物奇观", "摄影写真"], ["暗光产品", "电商营销"], ["亮调产品", "电商营销"],
  ["原生相机", "摄影写真"], ["CCD风", "摄影写真"], ["古早dv风", "摄影写真"], ["梦幻治愈系画风", "风格插画"],
  ["电商室内场景奶油风", "电商营销"], ["蜡笔风质感卡通头像", "动漫游戏"], ["国风金箔岩彩画", "风格插画"], ["古代中国画", "风格插画"],
].map(([name, category], i) => ({
  id: `style_${i + 1}`,
  name,
  category,
  hue: (i * 53 + 120) % 360,
  commercial: true,
  likes: 50 + i * 37,
}));

export const STYLE_CATEGORIES = ["推荐", "Midjourney", "摄影写真", "电商营销", "动漫游戏", "风格插画", "平面设计", "建筑空间"];

export const EFFECT_PRESETS = [
  "双人对打", "复古马卡龙", "穿越机运镜", "环球缩放",
  "清风竹林", "AI 编舞", "粒子消散", "时间冻结",
].map((name, i) => ({
  id: `effect_${i + 1}`,
  name,
  hue: (i * 71 + 200) % 360,
  meta: "特效",
}));

export const TOOLBOX_PRESETS = [
  "左弧滑行", "电商手机弹出效果", "咖啡杯出场", "360旋转展示",
  "机械臂视角", "Live 2D",
].map((name, i) => ({
  id: `tool_${i + 1}`,
  name: `【预设】${name}`,
  hue: (i * 61 + 40) % 360,
  meta: "工具",
}));

export function coverGradient(hue) {
  return `linear-gradient(140deg, hsl(${hue} 24% 22%), hsl(${(hue + 40) % 360} 30% 14%))`;
}
