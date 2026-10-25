import { describe, expect, it } from "vitest";

import { latestCurrentCalendarDate } from "../../catalog/schema/resource.js";

describe("calendar-date validation boundary", () => {
  it("accepts a civil date that is already current in UTC+14", () => {
    expect(
      latestCurrentCalendarDate(new Date("2026-09-04T16:30:00.000Z")),
    ).toBe("2026-09-05");
  });

  it("does not advance before the earliest next civil date exists", () => {
    expect(
      latestCurrentCalendarDate(new Date("2026-09-04T09:30:00.000Z")),
    ).toBe("2026-09-04");
  });
});
