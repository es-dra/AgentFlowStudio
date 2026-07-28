import landscapeImage from "../../../studio/assets/test-fixtures/image-admission-review-landscape.png";
import portraitImage from "../../../studio/assets/test-fixtures/image-admission-review-portrait.png";
import squareImage from "../../../studio/assets/test-fixtures/image-admission-review-square.png";

export interface CanonicalScene {
  sceneRef: string;
  sequence: number;
  title: string;
  durationSeconds: number;
  shotRefs: string[];
}

export interface CanonicalShot {
  shotRef: string;
  sequence: number;
  sceneRef: string;
  displayName: string;
  durationSeconds: number;
  shotSize: string;
  intent: string;
  keyframeStatus: "adopted" | "generating";
  videoStatus: "adopted" | "review_pending" | "not_started";
  imageUrl: string;
}

export interface CanonicalCandidate {
  candidateRef: string;
  entityRef: string;
  mediaType: "视频" | "图片";
  sequence: number;
  reviewState: "superseded" | "pending";
  adoptionState: "not_adopted";
  durationSeconds?: number;
  qualityIssue?: {
    rangeStartSeconds: number;
    rangeEndSeconds: number;
    summary: string;
  };
  imageUrl: string;
}

export interface CanonicalFixture {
  fixtureVersion: "0.2";
  project: {
    projectId: string;
    displayName: string;
    episodeName: string;
    targetDurationSeconds: number;
    projectVersion: number;
    lastCheckpointAt: string;
    resumeTarget: {
      surface: "review";
      entityRef: string;
      reason: string;
    };
  };
  scenes: CanonicalScene[];
  shots: CanonicalShot[];
  candidates: CanonicalCandidate[];
  assets: Array<{
    assetRef: string;
    assetType: string;
    displayName: string;
    mediaStatus: "adopted" | "review_pending";
    referencedByShots: string[];
  }>;
  tasks: Array<{
    taskRef: string;
    taskType: string;
    entityRef: string;
    state: "running";
    progressPercent: number;
    recoveryState: "durable";
    estimatedCostCny: number;
  }>;
  delivery: {
    deliveryVersion: number;
    state: "blocked";
    playableDurationSeconds: number;
    blockers: string[];
  };
  budget: {
    currency: "CNY";
    used: number;
    reserved: number;
  };
}

export const canonicalFixture: CanonicalFixture = {
  fixtureVersion: "0.2",
  project: {
    projectId: "studio-1785154250742-86s0uf",
    displayName: "雾港来信",
    episodeName: "第一集·启程前",
    targetDurationSeconds: 77,
    projectVersion: 32,
    lastCheckpointAt: "2026-07-29T14:32:00+08:00",
    resumeTarget: {
      surface: "review",
      entityRef: "candidate-shot-03-video-v2",
      reason: "镜头 03 有两个视频候选等待决定"
    }
  },
  scenes: [
    {
      sceneRef: "scene-01",
      sequence: 1,
      title: "雾港启程",
      durationSeconds: 22,
      shotRefs: ["shot-01", "shot-02"]
    },
    {
      sceneRef: "scene-02",
      sequence: 2,
      title: "灯塔警示",
      durationSeconds: 28,
      shotRefs: ["shot-03", "shot-04", "shot-05"]
    },
    {
      sceneRef: "scene-03",
      sequence: 3,
      title: "穿过码头",
      durationSeconds: 27,
      shotRefs: ["shot-06", "shot-07"]
    }
  ],
  shots: [
    {
      shotRef: "shot-01",
      sequence: 1,
      sceneRef: "scene-01",
      displayName: "雾港全景",
      durationSeconds: 12,
      shotSize: "远景",
      intent: "帆船穿过晨雾，港口逐渐显出轮廓",
      keyframeStatus: "adopted",
      videoStatus: "adopted",
      imageUrl: landscapeImage
    },
    {
      shotRef: "shot-02",
      sequence: 2,
      sceneRef: "scene-01",
      displayName: "阿岚登船",
      durationSeconds: 10,
      shotSize: "中景",
      intent: "阿岚回望码头，把信件藏入外套",
      keyframeStatus: "adopted",
      videoStatus: "adopted",
      imageUrl: portraitImage
    },
    {
      shotRef: "shot-03",
      sequence: 3,
      sceneRef: "scene-02",
      displayName: "灯塔远景",
      durationSeconds: 8,
      shotSize: "远景",
      intent: "灯塔光穿过浓雾，海浪逐渐增强",
      keyframeStatus: "adopted",
      videoStatus: "review_pending",
      imageUrl: landscapeImage
    },
    {
      shotRef: "shot-04",
      sequence: 4,
      sceneRef: "scene-02",
      displayName: "船长转身",
      durationSeconds: 11,
      shotSize: "中景",
      intent: "老船长在雨中转身，视线掠过灯塔",
      keyframeStatus: "adopted",
      videoStatus: "adopted",
      imageUrl: portraitImage
    },
    {
      shotRef: "shot-05",
      sequence: 5,
      sceneRef: "scene-02",
      displayName: "检查设备",
      durationSeconds: 9,
      shotSize: "近景",
      intent: "船员检查设备，为离港做最后准备",
      keyframeStatus: "generating",
      videoStatus: "not_started",
      imageUrl: squareImage
    },
    {
      shotRef: "shot-06",
      sequence: 6,
      sceneRef: "scene-03",
      displayName: "小船入潮",
      durationSeconds: 14,
      shotSize: "远景",
      intent: "小船驶入潮汐，雾港灯火逐渐远去",
      keyframeStatus: "adopted",
      videoStatus: "adopted",
      imageUrl: landscapeImage
    },
    {
      shotRef: "shot-07",
      sequence: 7,
      sceneRef: "scene-03",
      displayName: "巷口微光",
      durationSeconds: 13,
      shotSize: "远景",
      intent: "巷口最后一盏灯熄灭，留下未寄出的回音",
      keyframeStatus: "adopted",
      videoStatus: "not_started",
      imageUrl: landscapeImage
    }
  ],
  candidates: [
    {
      candidateRef: "candidate-shot-03-video-v1",
      entityRef: "shot-03",
      mediaType: "视频",
      sequence: 1,
      reviewState: "superseded",
      adoptionState: "not_adopted",
      durationSeconds: 8,
      imageUrl: landscapeImage
    },
    {
      candidateRef: "candidate-shot-03-video-v2",
      entityRef: "shot-03",
      mediaType: "视频",
      sequence: 2,
      reviewState: "pending",
      adoptionState: "not_adopted",
      durationSeconds: 8,
      qualityIssue: {
        rangeStartSeconds: 6,
        rangeEndSeconds: 8,
        summary: "灯塔光束在结尾有轻微跳变"
      },
      imageUrl: landscapeImage
    },
    {
      candidateRef: "candidate-asset-letter-image-v1",
      entityRef: "asset-prop-letter",
      mediaType: "图片",
      sequence: 1,
      reviewState: "pending",
      adoptionState: "not_adopted",
      imageUrl: squareImage
    }
  ],
  assets: [
    {
      assetRef: "asset-character-alan",
      assetType: "人物",
      displayName: "阿岚",
      mediaStatus: "adopted",
      referencedByShots: ["shot-02"]
    },
    {
      assetRef: "asset-character-captain",
      assetType: "人物",
      displayName: "老船长",
      mediaStatus: "adopted",
      referencedByShots: ["shot-04", "shot-05"]
    },
    {
      assetRef: "asset-location-harbor",
      assetType: "场景",
      displayName: "雾港",
      mediaStatus: "adopted",
      referencedByShots: ["shot-01", "shot-02", "shot-06", "shot-07"]
    },
    {
      assetRef: "asset-location-lighthouse",
      assetType: "场景",
      displayName: "灯塔",
      mediaStatus: "adopted",
      referencedByShots: ["shot-03", "shot-04"]
    },
    {
      assetRef: "asset-location-dock",
      assetType: "场景",
      displayName: "码头",
      mediaStatus: "adopted",
      referencedByShots: ["shot-01", "shot-02", "shot-05", "shot-06", "shot-07"]
    },
    {
      assetRef: "asset-prop-letter",
      assetType: "道具",
      displayName: "油布包裹的信件",
      mediaStatus: "review_pending",
      referencedByShots: ["shot-02", "shot-07"]
    }
  ],
  tasks: [
    {
      taskRef: "task-shot-05-keyframe",
      taskType: "关键画面制作",
      entityRef: "shot-05",
      state: "running",
      progressPercent: 46,
      recoveryState: "durable",
      estimatedCostCny: 3.2
    }
  ],
  delivery: {
    deliveryVersion: 3,
    state: "blocked",
    playableDurationSeconds: 47,
    blockers: [
      "镜头 03 视频候选待审核",
      "镜头 05 关键画面正在制作",
      "镜头 07 视频尚未制作"
    ]
  },
  budget: {
    currency: "CNY",
    used: 186.4,
    reserved: 9.5
  }
};
