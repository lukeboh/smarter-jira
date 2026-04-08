import { describe, it, expect, vi } from "vitest";
import { createLogger } from "@core/logging";

describe("createLogger", () => {
  it("respeita nível mínimo", () => {
    const debug = vi.spyOn(console, "debug").mockImplementation(() => {});
    const info = vi.spyOn(console, "info").mockImplementation(() => {});
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const error = vi.spyOn(console, "error").mockImplementation(() => {});

    const logger = createLogger("warn");
    logger.debug("debug");
    logger.info("info");
    logger.warn("warn");
    logger.error("error");

    expect(debug).not.toHaveBeenCalled();
    expect(info).not.toHaveBeenCalled();
    expect(warn).toHaveBeenCalled();
    expect(error).toHaveBeenCalled();

    debug.mockRestore();
    info.mockRestore();
    warn.mockRestore();
    error.mockRestore();
  });
});
