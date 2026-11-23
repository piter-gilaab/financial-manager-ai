import { describe, expect, it } from "vitest";
import { displayDomain, displayLimitation, displayReason, displayStatus, shortDatasetId } from "@/lib/presentation";

describe("product presentation language", () => {
  it("translates authority codes without changing the source identifier", () => {
    expect(displayDomain("PAYABLE")).toBe("Accounts payable");
    expect(displayReason("MISSING_REQUIRED_SEMANTICS")).toBe("Required financial meaning is not confirmed.");
    expect(displayStatus("SUPPORTED")).toBe("Ready");
    expect(displayReason("binding_validation_returned_missing_required_semantics")).toBe("Required financial meaning is not confirmed.");
    expect(displayReason("Binding validation returned MISSING_REQUIRED_SEMANTICS.")).toBe("Required financial meaning is not confirmed.");
    expect(displayLimitation("Only GLOBAL screening under tukey_iqr v1.0 is supported.")).toBe("Screening uses one global statistical range across the selected measure.");
  });

  it("provides a bounded display id while preserving the exact value separately", () => {
    expect(shortDatasetId("ds_12345678901234567890")).toBe("ds_123…567890");
  });
});
