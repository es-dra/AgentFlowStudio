import { useState } from "react";
import {
  IconMaximize,
  IconPlayerPauseFilled,
  IconPlayerPlayFilled,
  IconVolume
} from "@tabler/icons-react";

interface MediaStageProps {
  imageUrl: string;
  title: string;
  durationSeconds: number;
  rangeStart?: number;
  rangeEnd?: number;
}

export function MediaStage({
  imageUrl,
  title,
  durationSeconds,
  rangeStart,
  rangeEnd
}: MediaStageProps) {
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const hasRange = rangeStart !== undefined && rangeEnd !== undefined;

  return (
    <figure className="media-stage">
      <div className="media-stage__image">
        <img src={imageUrl} alt={`${title}的媒体预览`} />
        {playing ? <span className="media-stage__playing">预览播放中</span> : null}
      </div>
      <figcaption className="media-controls">
        <button
          className="icon-button"
          type="button"
          aria-label={playing ? "暂停预览" : "播放预览"}
          title={playing ? "暂停预览" : "播放预览"}
          onClick={() => setPlaying((value) => !value)}
        >
          {playing ? (
            <IconPlayerPauseFilled aria-hidden="true" size={18} />
          ) : (
            <IconPlayerPlayFilled aria-hidden="true" size={18} />
          )}
        </button>
        <span>{formatSeconds(currentTime)} / {formatSeconds(durationSeconds)}</span>
        <div className="media-range-wrap">
          <input
            aria-label="预览时间"
            type="range"
            min={0}
            max={durationSeconds}
            step={0.1}
            value={currentTime}
            onChange={(event) => setCurrentTime(Number(event.target.value))}
          />
          {hasRange ? (
            <span
              className="media-range-marker"
              style={{
                left: `${(rangeStart / durationSeconds) * 100}%`,
                width: `${((rangeEnd - rangeStart) / durationSeconds) * 100}%`
              }}
              aria-hidden="true"
            />
          ) : null}
        </div>
        <IconVolume aria-label="声音可用" size={18} />
        <button
          className="icon-button"
          type="button"
          aria-label="全屏预览"
          title="全屏预览"
        >
          <IconMaximize aria-hidden="true" size={18} />
        </button>
      </figcaption>
    </figure>
  );
}

export function formatSeconds(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.floor(seconds % 60);
  return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}
