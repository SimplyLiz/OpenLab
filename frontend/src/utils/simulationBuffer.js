class SimulationBuffer {
    _data = [];
    _version = 0;
    get version() {
        return this._version;
    }
    get data() {
        return this._data;
    }
    get length() {
        return this._data.length;
    }
    push(snapshot) {
        this._data.push(snapshot);
        this._version++;
    }
    clear() {
        this._data = [];
        this._version = 0;
    }
}
export const simulationBuffer = new SimulationBuffer();
