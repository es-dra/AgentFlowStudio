export const CAMERA_BODIES = ["Panavision DXL2", "ARRI Alexa 65", "RED V-Raptor", "Sony Venice 2"];
export const CAMERA_LENSES = ["Arri Signature Prime", "Cooke S7/i", "Zeiss Supreme Prime", "Canon K35"];
export const CAMERA_FOCALS = ["24", "35", "50", "85", "135"];
export const CAMERA_APERTURES = ["f/1.4", "f/2", "f/2.8", "f/4", "f/5.6"];

export function defaultCameraSetup() {
  return {
    body: CAMERA_BODIES[0],
    lens: CAMERA_LENSES[0],
    focal: "35",
    aperture: "f/4",
  };
}

export function cameraSummary(setup) {
  return `${setup.body} · ${setup.lens} · ${setup.focal}mm · ${setup.aperture}`;
}
