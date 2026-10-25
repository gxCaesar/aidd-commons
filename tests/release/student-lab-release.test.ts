import {
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, it } from "vitest";
import { buildPublicRelease } from "../../scripts/release/build.js";

it("curates runnable student source and documentation without student outputs", async () => {
  const root = await mkdtemp(join(tmpdir(), "aidd-student-release-"));
  const source = join(root, "source");
  const student = join(source, "labs", "student_modelling");
  await mkdir(student, { recursive: true });
  await mkdir(join(source, "tmp", "student-modelling"), { recursive: true });
  for (const name of ["run_lab.py", "README.md"]) {
    await copyFile(`labs/student_modelling/${name}`, join(student, name));
  }
  await writeFile(
    join(student, "private-attempt.json"),
    '{"student":"private"}',
  );
  await writeFile(
    join(source, "tmp", "student-modelling", "report.json"),
    '{"student":"private"}',
  );
  const destination = join(root, "public-release");
  const result = await buildPublicRelease({
    sourceRoot: source,
    destination,
    inventoryPath: join(root, "inventory.txt"),
  });
  const paths = result.files.map((entry) => entry.path);
  expect(paths).toContain("labs/student_modelling/run_lab.py");
  expect(paths).toContain("labs/student_modelling/README.md");
  expect(
    paths.some(
      (path) =>
        path.includes("private-attempt") || path.includes("report.json"),
    ),
  ).toBe(false);
  expect(result.findings).toEqual([]);
  expect(
    await readFile(
      join(destination, "labs/student_modelling/run_lab.py"),
      "utf8",
    ),
  ).toBe(await readFile("labs/student_modelling/run_lab.py", "utf8"));
});
