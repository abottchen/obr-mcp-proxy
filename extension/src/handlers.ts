import OBR, { type Item, type Metadata, type Vector2 } from "@owlbear-rodeo/sdk";

type Handler = (params: Record<string, unknown>) => Promise<unknown>;

const handlers: Record<string, Handler> = {
  // Scene items — read
  "scene.items.getItems": async () => {
    return await OBR.scene.items.getItems();
  },

  // Scene items — mutate
  "scene.items.updateItems": async (params) => {
    const updates = params.items as Array<Record<string, unknown>>;
    for (const update of updates) {
      const { id, ...fields } = update;
      await OBR.scene.items.updateItems([id as string], (drafts) => {
        for (const draft of drafts) {
          // Merge metadata rather than replacing it
          if (fields.metadata && draft.metadata) {
            Object.assign(draft.metadata, fields.metadata as Metadata);
            delete fields.metadata;
          }
          Object.assign(draft, fields);
        }
      });
    }
  },

  "scene.items.addItems": async (params) => {
    await OBR.scene.items.addItems(params.items as Item[]);
  },

  "scene.items.deleteItems": async (params) => {
    await OBR.scene.items.deleteItems(params.ids as string[]);
  },

  // Scene metadata
  "scene.getMetadata": async () => {
    return await OBR.scene.getMetadata();
  },

  "scene.setMetadata": async (params) => {
    await OBR.scene.setMetadata(params.metadata as Metadata);
  },

  // Grid
  "scene.grid.getScale": async () => {
    return await OBR.scene.grid.getScale();
  },

  "scene.grid.getDpi": async () => {
    return await OBR.scene.grid.getDpi();
  },

  "scene.grid.getType": async () => {
    return await OBR.scene.grid.getType();
  },

  "scene.grid.getMeasurement": async () => {
    return await OBR.scene.grid.getMeasurement();
  },

  "scene.grid.snapPosition": async (params) => {
    const snappingSensitivity = (params.snappingSensitivity as number) ?? 1;
    const useCorners = (params.useCorners as boolean) ?? false;
    const useCenter = (params.useCenter as boolean) ?? true;
    return await OBR.scene.grid.snapPosition(
      params.position as Vector2,
      snappingSensitivity,
      useCorners,
      useCenter
    );
  },

  "scene.grid.getDistance": async (params) => {
    return await OBR.scene.grid.getDistance(
      params.from as Vector2,
      params.to as Vector2
    );
  },

  // Players
  "party.getPlayers": async () => {
    return await OBR.party.getPlayers();
  },
};

export function dispatch(
  method: string,
  params: Record<string, unknown>
): Promise<unknown> {
  const handler = handlers[method];
  if (!handler) {
    return Promise.reject(new Error(`Unknown method: ${method}`));
  }
  return handler(params);
}
