import { useMicVAD } from "@ricky0123/vad-react";
import { useEffect, useState } from "react";

export interface VADFilterOptions {
  onSpeechStart?: () => void;
  onSpeechEnd?: (audio: Float32Array) => void;
  startOnLoad?: boolean;
}

export interface VADFilterResult {
  start: () => void;
  pause: () => void;
  listening: boolean;
  userSpeaking: boolean;
  errored: boolean;
  loading: boolean;
}

export const useVADFilter = ({
  onSpeechStart,
  onSpeechEnd,
  startOnLoad = true,
}: VADFilterOptions): VADFilterResult => {
  const [errored, setErrored] = useState(false);

  const vad = useMicVAD({
    startOnLoad,
    baseAssetPath: "/assets/vad/",
    onnxWASMBasePath: "/assets/vad/",
    onSpeechStart,
    onSpeechEnd,
    ortConfig: (ort) => {
      // Configure ONNX Runtime to use local WASM files
      ort.env.wasm.wasmPaths = "/assets/vad/";
      ort.env.wasm.numThreads = 1; 
      ort.env.wasm.simd = true;
    },
    onVADMisfire: () => {
      // Optional: handle short noise bursts if needed
    },
  });

  useEffect(() => {
    if (vad.errored) {
      console.error("VAD Error:", vad.errored);
      setErrored(true);
    }
  }, [vad.errored]);

  return {
    start: vad.start,
    pause: vad.pause,
    listening: vad.listening,
    userSpeaking: vad.userSpeaking,
    errored,
    loading: vad.loading,
  };
};
