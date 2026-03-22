import OBR, {
  buildCurve,
  buildImage,
  buildLabel,
  buildLine,
  buildPath,
  buildShape,
  buildText,
  type Item,
  type Layer,
  type Metadata,
  type PathCommand,
  type Vector2,
} from "@owlbear-rodeo/sdk";

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
    const specs = params.items as Array<Record<string, unknown>>;
    const built: Item[] = [];
    for (const spec of specs) {
      const itemType = spec.type as string;
      const pos = spec.position as Vector2;
      const meta = (spec.metadata as Metadata) ?? {};
      const layer = (spec.layer as Layer) ?? "CHARACTER";

      const specId = spec.id as string | undefined;

      if (itemType === "IMAGE") {
        const img = spec.image as { url: string; width: number; height: number; mime: string };
        const grid = spec.grid as { dpi: number; offset: { x: number; y: number } };
        const builder = buildImage(
          { url: img.url, width: img.width, height: img.height, mime: img.mime },
          { dpi: grid.dpi, offset: grid.offset }
        )
          .position(pos)
          .name((spec.name as string) ?? "")
          .plainText((spec.name as string) ?? "")
          .layer(layer)
          .visible((spec.visible as boolean) ?? true)
          .locked((spec.locked as boolean) ?? false)
          .metadata(meta);
        if (specId) builder.id(specId);
        built.push(builder.build());
      } else if (itemType === "SHAPE") {
        const style = spec.style as Record<string, unknown> | undefined;
        const builder = buildShape()
          .position(pos)
          .name((spec.name as string) ?? "")
          .layer(layer)
          .visible((spec.visible as boolean) ?? true)
          .locked((spec.locked as boolean) ?? false)
          .metadata(meta);
        if (spec.shapeType != null) builder.shapeType(spec.shapeType as "RECTANGLE" | "CIRCLE" | "TRIANGLE" | "HEXAGON");
        if (spec.width != null) builder.width(spec.width as number);
        if (spec.height != null) builder.height(spec.height as number);
        if (style) {
          if (style.fillColor != null) builder.fillColor(style.fillColor as string);
          if (style.fillOpacity != null) builder.fillOpacity(style.fillOpacity as number);
          if (style.strokeColor != null) builder.strokeColor(style.strokeColor as string);
          if (style.strokeOpacity != null) builder.strokeOpacity(style.strokeOpacity as number);
          if (style.strokeWidth != null) builder.strokeWidth(style.strokeWidth as number);
          if (style.strokeDash != null) builder.strokeDash(style.strokeDash as number[]);
        }
        if (specId) builder.id(specId);
        built.push(builder.build());
      } else if (itemType === "TEXT") {
        const textStyle = spec.textStyle as Record<string, unknown> | undefined;
        const builder = buildText()
          .position(pos)
          .name((spec.name as string) ?? "")
          .plainText((spec.text as string) ?? "")
          .layer(layer)
          .visible((spec.visible as boolean) ?? true)
          .locked((spec.locked as boolean) ?? false)
          .metadata(meta);
        if (textStyle) {
          if (textStyle.fontFamily != null) builder.fontFamily(textStyle.fontFamily as string);
          if (textStyle.fontSize != null) builder.fontSize(textStyle.fontSize as number);
          if (textStyle.fontWeight != null) builder.fontWeight(textStyle.fontWeight as number);
          if (textStyle.textAlign != null) builder.textAlign(textStyle.textAlign as "LEFT" | "CENTER" | "RIGHT");
          if (textStyle.textAlignVertical != null) builder.textAlignVertical(textStyle.textAlignVertical as "BOTTOM" | "MIDDLE" | "TOP");
          if (textStyle.fillColor != null) builder.fillColor(textStyle.fillColor as string);
          if (textStyle.fillOpacity != null) builder.fillOpacity(textStyle.fillOpacity as number);
          if (textStyle.strokeColor != null) builder.strokeColor(textStyle.strokeColor as string);
          if (textStyle.strokeOpacity != null) builder.strokeOpacity(textStyle.strokeOpacity as number);
          if (textStyle.strokeWidth != null) builder.strokeWidth(textStyle.strokeWidth as number);
          if (textStyle.lineHeight != null) builder.lineHeight(textStyle.lineHeight as number);
          if (textStyle.padding != null) builder.padding(textStyle.padding as number);
          if (textStyle.width != null) builder.width(textStyle.width as number | "AUTO");
          if (textStyle.height != null) builder.height(textStyle.height as number | "AUTO");
        }
        if (specId) builder.id(specId);
        built.push(builder.build());
      } else if (itemType === "LABEL") {
        const textStyle = spec.textStyle as Record<string, unknown> | undefined;
        const labelStyle = spec.labelStyle as Record<string, unknown> | undefined;
        const builder = buildLabel()
          .position(pos)
          .name((spec.name as string) ?? "")
          .plainText((spec.text as string) ?? "")
          .layer(layer)
          .visible((spec.visible as boolean) ?? true)
          .locked((spec.locked as boolean) ?? false)
          .metadata(meta);
        if (textStyle) {
          if (textStyle.fontFamily != null) builder.fontFamily(textStyle.fontFamily as string);
          if (textStyle.fontSize != null) builder.fontSize(textStyle.fontSize as number);
          if (textStyle.fontWeight != null) builder.fontWeight(textStyle.fontWeight as number);
          if (textStyle.textAlign != null) builder.textAlign(textStyle.textAlign as "LEFT" | "CENTER" | "RIGHT");
          if (textStyle.textAlignVertical != null) builder.textAlignVertical(textStyle.textAlignVertical as "BOTTOM" | "MIDDLE" | "TOP");
          if (textStyle.fillColor != null) builder.fillColor(textStyle.fillColor as string);
          if (textStyle.fillOpacity != null) builder.fillOpacity(textStyle.fillOpacity as number);
          if (textStyle.strokeColor != null) builder.strokeColor(textStyle.strokeColor as string);
          if (textStyle.strokeOpacity != null) builder.strokeOpacity(textStyle.strokeOpacity as number);
          if (textStyle.strokeWidth != null) builder.strokeWidth(textStyle.strokeWidth as number);
          if (textStyle.lineHeight != null) builder.lineHeight(textStyle.lineHeight as number);
          if (textStyle.padding != null) builder.padding(textStyle.padding as number);
          if (textStyle.width != null) builder.width(textStyle.width as number | "AUTO");
          if (textStyle.height != null) builder.height(textStyle.height as number | "AUTO");
        }
        if (labelStyle) {
          if (labelStyle.backgroundColor != null) builder.backgroundColor(labelStyle.backgroundColor as string);
          if (labelStyle.backgroundOpacity != null) builder.backgroundOpacity(labelStyle.backgroundOpacity as number);
          if (labelStyle.cornerRadius != null) builder.cornerRadius(labelStyle.cornerRadius as number);
          if (labelStyle.pointerWidth != null) builder.pointerWidth(labelStyle.pointerWidth as number);
          if (labelStyle.pointerHeight != null) builder.pointerHeight(labelStyle.pointerHeight as number);
          if (labelStyle.pointerDirection != null) builder.pointerDirection(labelStyle.pointerDirection as "UP" | "DOWN" | "LEFT" | "RIGHT");
          if (labelStyle.maxViewScale != null) builder.maxViewScale(labelStyle.maxViewScale as number);
          if (labelStyle.minViewScale != null) builder.minViewScale(labelStyle.minViewScale as number);
        }
        if (specId) builder.id(specId);
        built.push(builder.build());
      } else if (itemType === "LINE") {
        const startPos = (spec.startPosition as Vector2) ?? pos;
        const endPos = spec.endPosition as Vector2;
        const style = spec.style as Record<string, unknown> | undefined;
        const builder = buildLine()
          .position(pos)
          .startPosition(startPos)
          .endPosition(endPos)
          .name((spec.name as string) ?? "")
          .layer(layer)
          .visible((spec.visible as boolean) ?? true)
          .locked((spec.locked as boolean) ?? false)
          .metadata(meta);
        if (style) {
          if (style.strokeColor != null) builder.strokeColor(style.strokeColor as string);
          if (style.strokeOpacity != null) builder.strokeOpacity(style.strokeOpacity as number);
          if (style.strokeWidth != null) builder.strokeWidth(style.strokeWidth as number);
          if (style.strokeDash != null) builder.strokeDash(style.strokeDash as number[]);
        }
        if (specId) builder.id(specId);
        built.push(builder.build());
      } else if (itemType === "CURVE") {
        const points = spec.points as Vector2[];
        const style = spec.style as Record<string, unknown> | undefined;
        const builder = buildCurve()
          .position(pos)
          .points(points)
          .name((spec.name as string) ?? "")
          .layer(layer)
          .visible((spec.visible as boolean) ?? true)
          .locked((spec.locked as boolean) ?? false)
          .metadata(meta);
        if (style) {
          if (style.fillColor != null) builder.fillColor(style.fillColor as string);
          if (style.fillOpacity != null) builder.fillOpacity(style.fillOpacity as number);
          if (style.strokeColor != null) builder.strokeColor(style.strokeColor as string);
          if (style.strokeOpacity != null) builder.strokeOpacity(style.strokeOpacity as number);
          if (style.strokeWidth != null) builder.strokeWidth(style.strokeWidth as number);
          if (style.strokeDash != null) builder.strokeDash(style.strokeDash as number[]);
          if (style.tension != null) builder.tension(style.tension as number);
          if (style.closed != null) builder.closed(style.closed as boolean);
        }
        if (specId) builder.id(specId);
        built.push(builder.build());
      } else if (itemType === "PATH") {
        const commands = spec.commands as PathCommand[];
        const style = spec.style as Record<string, unknown> | undefined;
        const builder = buildPath()
          .position(pos)
          .commands(commands)
          .name((spec.name as string) ?? "")
          .layer(layer)
          .visible((spec.visible as boolean) ?? true)
          .locked((spec.locked as boolean) ?? false)
          .metadata(meta);
        if (spec.fillRule != null) builder.fillRule(spec.fillRule as string);
        if (style) {
          if (style.fillColor != null) builder.fillColor(style.fillColor as string);
          if (style.fillOpacity != null) builder.fillOpacity(style.fillOpacity as number);
          if (style.strokeColor != null) builder.strokeColor(style.strokeColor as string);
          if (style.strokeOpacity != null) builder.strokeOpacity(style.strokeOpacity as number);
          if (style.strokeWidth != null) builder.strokeWidth(style.strokeWidth as number);
          if (style.strokeDash != null) builder.strokeDash(style.strokeDash as number[]);
        }
        if (specId) builder.id(specId);
        built.push(builder.build());
      } else {
        throw new Error(`Unsupported item type: ${itemType}`);
      }
    }
    await OBR.scene.items.addItems(built);
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

  // Room metadata
  "room.getMetadata": async () => {
    return await OBR.room.getMetadata();
  },

  "room.setMetadata": async (params) => {
    await OBR.room.setMetadata(params.metadata as Metadata);
  },

  // Player
  "player.getId": async () => {
    return await OBR.player.getId();
  },

  "player.getMetadata": async () => {
    return await OBR.player.getMetadata();
  },

  "player.setMetadata": async (params) => {
    await OBR.player.setMetadata(params.metadata as Metadata);
  },

  // Party
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
