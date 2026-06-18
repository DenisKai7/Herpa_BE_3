export type HerpaSseEvent =
  | "message.started"
  | "retrieval.started"
  | "retrieval.completed"
  | "generation.started"
  | "validation.started"
  | "refinement.started"
  | "token"
  | "message.completed"
  | "message.failed";

export async function streamChat(
  body: unknown,
  token: string,
  onEvent: (event: HerpaSseEvent, data: unknown) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/chat/message/stream`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
      signal,
    },
  );
  if (!response.ok || !response.body) throw new Error(`Streaming gagal: ${response.status}`);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const event = frame.match(/^event: (.+)$/m)?.[1] as HerpaSseEvent | undefined;
      const raw = frame.match(/^data: (.+)$/m)?.[1];
      if (event && raw) onEvent(event, JSON.parse(raw));
    }
  }
}
