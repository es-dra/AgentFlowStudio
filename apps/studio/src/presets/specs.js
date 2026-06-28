export const IMAGE_QUALITY = ["低画质", "标准画质", "高画质"];
export const IMAGE_RESOLUTION = ["1K", "2K", "4K"];
export const IMAGE_RATIOS = [
  "自适应", "1:1", "1:2", "2:1", "9:16",
  "16:9", "3:4", "4:3", "3:2", "2:3",
  "5:4", "4:5", "21:9", "9:21",
];

export const VIDEO_RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4"];
export const VIDEO_RESOLUTIONS = ["480P", "720P"];
export const VIDEO_DURATIONS = ["5s", "10s"];

export const IMAGE_COUNTS = [1, 2, 4];
export const VIDEO_COUNTS = [1];

export const VIDEO_MODES = ["文生视频", "全能参考", "图生视频", "首尾帧", "图片参考"];

export function defaultImageSpec() {
  return { quality: "标准画质", resolution: "2K", ratio: "自适应", count: 1, panorama: false };
}

export function defaultVideoSpec() {
  return { ratio: "16:9", resolution: "720P", duration: "5s", sound: false, count: 1, mode: "文生视频" };
}

export function imageSpecLabel(spec) {
  return `${spec.panorama ? "2:1" : spec.ratio} · ${spec.quality} · ${spec.resolution}`;
}

export function videoSpecLabel(spec) {
  return `${spec.ratio} · ${spec.resolution} · ${spec.duration}`;
}
