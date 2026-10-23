import { useEffect, useState } from "react";

export type AsyncState<T> = { status: "loading" } | { status: "error"; error: string } | { status: "ready"; data: T };

export function useAsync<T>(load: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: "loading" });
  useEffect(() => {
    let live = true;
    setState({ status: "loading" });
    load().then((data) => live && setState({ status: "ready", data }))
          .catch((e: Error) => live && setState({ status: "error", error: e.message }));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}
