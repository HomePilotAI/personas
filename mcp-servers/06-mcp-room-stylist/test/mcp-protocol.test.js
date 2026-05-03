import { runProtocolHarness } from "@homepilot/mcp-node-common/test-helpers/protocol-harness";
import { tools } from "../src/tools.js";

runProtocolHarness({
  name: "mcp-room-stylist",
  version: "1.0.0",
  tools,
  sampleArgs: {
    room_layout: { room: "living", length_m: 5.2, width_m: 3.6, options: 2 },
    room_palette: { room: "bedroom", mood: "earth_organic" },
    room_shopping_list: { room: "office", palette: "cool_modern", budget: "balanced" },
  },
  invalidArgs: {
    room_layout: { room: "not-a-room" },
    room_palette: { room: "living", mood: "not-a-palette" },
    room_shopping_list: { room: "living", budget: "infinite" },
  },
});
