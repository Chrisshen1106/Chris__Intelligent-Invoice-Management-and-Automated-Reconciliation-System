const modules = import.meta.glob('./*.js', { eager: true });
let handlers = [];

for (const path in modules) {
  if (path === './index.js') continue;
  const moduleHandlers = modules[path].default;
  if (Array.isArray(moduleHandlers)) {
    handlers.push(...moduleHandlers);
  } else if (moduleHandlers) {
    handlers.push(moduleHandlers);
  }
}

export default handlers;
