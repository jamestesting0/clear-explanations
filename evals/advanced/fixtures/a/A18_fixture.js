let reads = 0;
const secret = Symbol("secret");
const source = Object.create({ inherited: 9 });
Object.defineProperty(source, "hidden", { value: 7, enumerable: false });
source.meta = { tag: "old" };
source.created = new Date("2025-01-01T00:00:00.000Z");
source.optional = undefined;
Object.defineProperty(source, "amount", {
  enumerable: true,
  get() { reads += 1; return reads; }
});
source[secret] = "token";
const spread = { ...source };
const json = JSON.parse(JSON.stringify(source));
const cloned = structuredClone(source);
source.meta.tag = "new";
source.created.setUTCFullYear(2030);
for (const [name, value] of Object.entries({spread, json, cloned})) {
  console.log(name, JSON.stringify({
    tag: value.meta.tag,
    dateType: value.created instanceof Date ? "Date" : typeof value.created,
    year: value.created instanceof Date ? value.created.getUTCFullYear() : value.created,
    optionalOwn: Object.hasOwn(value, "optional"),
    amount: value.amount,
    hiddenOwn: Object.hasOwn(value, "hidden"),
    inheritedOwn: Object.hasOwn(value, "inherited"),
    secretOwn: Object.hasOwn(value, secret),
    amountGetter: typeof Object.getOwnPropertyDescriptor(value, "amount").get
  }));
}
console.log("reads", reads);
try { structuredClone({ run() {} }); }
catch (error) { console.log("function-clone", error.name); }
