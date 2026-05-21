let currentVideoUrl = "";

export function renderLocalVideoPreview(container, videoArtifact, copy) {
  revokeCurrentVideoUrl();
  container.replaceChildren();

  if (!videoArtifact?.localFile) {
    container.textContent = copy.emptyVideo;
    return;
  }

  currentVideoUrl = URL.createObjectURL(videoArtifact.localFile);
  const video = document.createElement("video");
  video.controls = true;
  video.preload = "metadata";
  video.src = currentVideoUrl;

  const mediaType = videoArtifact.mediaType || mediaTypeFor(videoArtifact.fileName);
  const compatibility = document.createElement("p");
  compatibility.className = "meta";
  compatibility.textContent = copy.videoSelected(videoArtifact.fileName);

  if (videoArtifact.fileName.toLowerCase().endsWith(".mov") && !video.canPlayType("video/quicktime")) {
    compatibility.textContent = `${compatibility.textContent} ${copy.movCompatibility}`;
  }
  if (mediaType && video.canPlayType(mediaType) === "") {
    video.addEventListener("error", () => {
      compatibility.textContent = `${copy.videoPlaybackError} ${videoArtifact.fileName}`;
    });
  }

  container.append(video, compatibility);
}

export function revokeCurrentVideoUrl() {
  if (currentVideoUrl) {
    URL.revokeObjectURL(currentVideoUrl);
    currentVideoUrl = "";
  }
}

function mediaTypeFor(fileName) {
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".mp4")) return "video/mp4";
  if (lower.endsWith(".webm")) return "video/webm";
  if (lower.endsWith(".mov")) return "video/quicktime";
  return "";
}
