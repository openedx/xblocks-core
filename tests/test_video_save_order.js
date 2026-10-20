/* Actual native plugin and clock formatter; bounded jQuery/DOM/HTTP protocols.
 * VIDEO_SAVE_STATE_SOURCE selects byte-identical parent source for controls.
 */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assets = path.join(__dirname, '../xblocks_contrib/video/assets/js/src');

function harness() {
    const requests = [];
    const events = {on() {return this;}, off() {return this;}};
    const underscore = {
        extend: (...args) => Object.assign(...args),
        has: (obj, key) => Object.prototype.hasOwnProperty.call(obj, key),
        isFinite: Number.isFinite,
        bindAll(obj, ...names) {names.forEach(name => {obj[name] = obj[name].bind(obj);});},
        once(fn) {let called = false; return function(...args) {
            if (!called) {called = true; return fn.apply(this, args);}
        };}
    };
    function $() {return events;}
    $.Deferred = () => ({resolve() {return this;}, promise() {return this;}});
    $.isPlainObject = obj => obj !== null && typeof obj === 'object';
    $.ajax = options => {
        const record = {...options, data: JSON.parse(JSON.stringify(options.data)), callbacks: []};
        requests.push(record);
        return {always(callback) {record.callbacks.push(callback);}};
    };
    const context = vm.createContext({$, _: underscore, window: {}});
    const clock = fs.readFileSync(path.join(assets, 'utils/time.js'), 'utf8').replace(/^export /gm, '');
    const plugin = fs.readFileSync(process.env.VIDEO_SAVE_STATE_SOURCE ||
        path.join(assets, '09_save_state_plugin.js'), 'utf8')
        .replace(/^import .*;\s*$/gm, '').replace(/^export default SaveStatePlugin;\s*$/gm, '');
    vm.runInContext(clock + '\n' + plugin, context);
    function create(url = '/owned/save_user_state') {
        const stored = {};
        const state = {config: {saveStateEnabled: true, saveStateUrl: url}, videoPlayer: {currentTime: 10},
            storage: {setItem(key, value) {stored[key] = value;}}, el: events};
        context.state = state;
        vm.runInContext('SaveStatePlugin(state, {}, {})', context);
        return {state, stored, plugin: state.videoSaveStatePlugin};
    }
    return {requests, create, settle(index, status = 'success') {
        requests[index].callbacks.forEach(callback => callback({}, status));
    }};
}

test('native position requests serialize older and newer state', () => {
    const h = harness(), v = h.create();
    v.plugin.saveState(true); v.state.videoPlayer.currentTime = 73; v.plugin.saveState(true);
    if (process.env.VIDEO_SAVE_CAPTURE) {
        fs.writeFileSync(process.env.VIDEO_SAVE_CAPTURE,
            JSON.stringify(h.requests.map(r => r.data), null, 2) + '\n');
    }
    assert.equal(h.requests.length, 1);
    assert.equal(h.requests[0].data.saved_video_position, '00:00:10');
    assert.equal(v.stored.savedVideoPosition, 73);
    h.settle(0);
    assert.equal(h.requests.length, 2);
    assert.equal(h.requests[1].data.saved_video_position, '00:01:13');
    assert.equal(h.requests[1].async, true);
    if (process.env.VIDEO_SAVE_CAPTURE) {
        fs.writeFileSync(process.env.VIDEO_SAVE_CAPTURE,
            JSON.stringify(h.requests.map(r => r.data), null, 2) + '\n');
    }
});

test('a failed request settles before the next queued save starts', () => {
    const h = harness(), v = h.create();
    v.plugin.saveState(true, {speed: '1.5'});
    v.plugin.saveState(true, {auto_advance: true});
    assert.equal(h.requests.length, 1);
    h.settle(0, 'error');
    assert.equal(h.requests.length, 2);
    assert.deepEqual(h.requests[1].data, {auto_advance: true});
});

test('unload does not dispatch a parallel save; destroyed-page delivery is unclaimed', () => {
    const h = harness(), v = h.create();
    v.plugin.saveState(true); v.state.videoPlayer.currentTime = 90; v.plugin.onUnload();
    assert.equal(h.requests.length, 1);
    // This callback requires a surviving context. Its absence leaves delivery unfulfilled.
    h.settle(0);
    assert.equal(h.requests.length, 2);
    assert.equal(h.requests[1].async, false);
    assert.equal(h.requests[1].data.saved_video_position, '00:01:30');
});

test('an idle synchronous save and disabled saves preserve native behavior', () => {
    const h = harness(), v = h.create();
    v.state.config.saveStateEnabled = false; v.plugin.saveState(true);
    assert.equal(h.requests.length, 0);
    v.state.config.saveStateEnabled = true; v.state.videoPlayer.currentTime = 3.1242;
    v.plugin.saveState(false);
    assert.equal(h.requests.length, 1);
    assert.equal(h.requests[0].async, false);
    assert.equal(h.requests[0].data.saved_video_position, '00:00:03');
});

test('queued data is a snapshot and instances have independent queues', () => {
    const h = harness(), a = h.create('/owned/a'), b = h.create('/owned/b');
    a.plugin.saveState(true);
    const data = {speed: '1.5'}; a.plugin.saveState(true, data); data.speed = '8';
    b.state.videoPlayer.currentTime = 42; b.plugin.saveState(true);
    assert.equal(h.requests.length, 2);
    assert.equal(h.requests[1].url, '/owned/b');
    h.settle(0);
    assert.equal(h.requests.length, 3);
    assert.equal(h.requests[2].url, '/owned/a');
    assert.deepEqual(h.requests[2].data, {speed: '1.5'});
});
