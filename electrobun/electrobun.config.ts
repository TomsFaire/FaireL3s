import type { ElectrobunConfig } from "electrobun";

export default {
  app: {
    name: "FaireL3s",
    identifier: "com.faire.lowerthirds",
    version: "0.0.8",
  },
  build: {
    views: {},
    copy: {
      "resources/python-backend": "resources/python-backend",
    },
  },
} satisfies ElectrobunConfig;
