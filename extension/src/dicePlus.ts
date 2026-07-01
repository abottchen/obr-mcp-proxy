import OBR from "@owlbear-rodeo/sdk";

// Stable, namespaced identity we own on both ends. dicex echoes this back as
// the prefix of the response channels (`{source}/roll-result`).
const SOURCE = "com.abottchen.obr-mcp-proxy";

const ROLL_REQUEST_CHANNEL = "dice-plus/roll-request";
const ROLL_RESULT_CHANNEL = `${SOURCE}/roll-result`;
const ROLL_ERROR_CHANNEL = `${SOURCE}/roll-error`;

// dicex handshake + 3D physics can take several seconds. Give it headroom but
// still fail cleanly if dicex is absent or the tab is inactive.
const ROLL_TIMEOUT_MS = 20000;

interface DicePlusDie {
  value: number;
  kept: boolean;
}

interface DicePlusGroup {
  description: string;
  diceType: string;
  dice: DicePlusDie[];
  total: number;
  isNegative: boolean;
}

interface RollResultMessage {
  rollId: string;
  result: {
    totalValue: number;
    rollSummary: string;
    groups: DicePlusGroup[];
  };
}

interface RollErrorMessage {
  rollId: string;
  error: string;
  notation: string;
}

export interface DiceRollResult {
  notation: string;
  total: number;
  summary: string;
  groups: {
    description: string;
    diceType: string;
    total: number;
    dice: DicePlusDie[];
  }[];
}

// dicex tracks only one pending Dice+ roll at a time (a module-global in its
// dicePlusPendingRequest.ts), so concurrent rolls clobber each other's result
// routing. The relay allows 3 concurrent requests and multiple Claude sessions
// can connect, so serialize every roll through this promise chain.
let queue: Promise<unknown> = Promise.resolve();

export function rollViaDicePlus(notation: string): Promise<DiceRollResult> {
  const run = () => rollOnce(notation);
  // Run after the previous roll settles, regardless of its outcome.
  const next = queue.then(run, run);
  // Keep the chain alive even if this roll rejects.
  queue = next.then(
    () => undefined,
    () => undefined
  );
  return next;
}

function rollOnce(notation: string): Promise<DiceRollResult> {
  return new Promise<DiceRollResult>((resolve, reject) => {
    const rollId = crypto.randomUUID();
    let settled = false;
    const teardowns: Array<() => void> = [];

    const cleanup = () => {
      for (const t of teardowns) t();
    };
    const finishOk = (value: DiceRollResult) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(value);
    };
    const finishErr = (err: Error) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(err);
    };

    teardowns.push(
      OBR.broadcast.onMessage(ROLL_RESULT_CHANNEL, (event) => {
        const data = event.data as RollResultMessage;
        if (data?.rollId !== rollId) return;
        try {
          const r = data.result;
          finishOk({
            notation,
            total: r.totalValue,
            summary: r.rollSummary,
            groups: r.groups.map((g) => ({
              description: g.description,
              diceType: g.diceType,
              total: g.total,
              dice: g.dice,
            })),
          });
        } catch (e) {
          finishErr(e instanceof Error ? e : new Error("Malformed dicex result"));
        }
      })
    );

    teardowns.push(
      OBR.broadcast.onMessage(ROLL_ERROR_CHANNEL, (event) => {
        const data = event.data as RollErrorMessage;
        if (data?.rollId !== rollId) return;
        finishErr(new Error(data.error));
      })
    );

    const timer = setTimeout(() => {
      finishErr(
        new Error(
          "dicex did not respond (is the dicex extension installed and this tab active?)"
        )
      );
    }, ROLL_TIMEOUT_MS);
    teardowns.push(() => clearTimeout(timer));

    OBR.broadcast
      .sendMessage(
        ROLL_REQUEST_CHANNEL,
        {
          rollId,
          playerId: OBR.player.id,
          playerName: "DM",
          rollTarget: "gm_only",
          diceNotation: notation,
          showResults: true,
          timestamp: Date.now(),
          source: SOURCE,
        },
        { destination: "LOCAL" }
      )
      .catch((e) => finishErr(e instanceof Error ? e : new Error(String(e))));
  });
}
