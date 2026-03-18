import OBR from "@owlbear-rodeo/sdk";

type Handler = (params: Record<string, unknown>) => Promise<unknown>;

const handlers: Record<string, Handler> = {
  "scene.items.getItems": async () => {
    return await OBR.scene.items.getItems();
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
