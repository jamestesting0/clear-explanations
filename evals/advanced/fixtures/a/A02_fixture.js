const trace = [];
const log = value => trace.push(value);
log("start");
Promise.resolve()
  .then(() => {
    log("first");
    queueMicrotask(() => log("nested"));
    return Promise.resolve("row");
  })
  .then(value => {
    log("write:" + value);
    throw new Error("write-failed");
  })
  .catch(error => {
    log("caught:" + error.message);
    return "fallback";
  })
  .finally(() => {
    log("audit");
    throw new Error("audit-failed");
  })
  .then(value => log("success:" + value),
        error => log("outer:" + error.message));
queueMicrotask(() => log("peer"));
(async () => { await 0; log("await-resumed"); })();
setTimeout(() => {
  log("timer");
  console.log(trace.join(" | "));
}, 0);
log("end");
