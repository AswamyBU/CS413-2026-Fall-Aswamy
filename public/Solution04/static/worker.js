importScripts('runtime.js');
self.onmessage = ({data}) => self.postMessage(LambdaRuntime.perform(data.operation, data.source));
