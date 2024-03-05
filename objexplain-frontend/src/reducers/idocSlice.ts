import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {ImageDocument} from "../api/models/imgdoc";
import {Label} from "../api/models/label";

interface iDocState {
    showObjects: boolean;
    objsVis: boolean[] | undefined;
    document: ImageDocument | undefined;
    annoMode: boolean;
    labelMap: [string, Label][] | undefined;
    numPrecached: number;
    fetchedIdx: number;
    fetchedDocs: ImageDocument[] | undefined;
    historyIdx: number;
    historyDocs: ImageDocument[] | undefined;
}

const initialState: iDocState = {
    showObjects: true,
    objsVis: undefined,
    document: undefined,
    annoMode: false,
    labelMap: undefined,
    numPrecached: 6,
    fetchedIdx: 0,
    fetchedDocs: undefined,
    historyIdx: 0,
    historyDocs: undefined,
};

export const idocSlice = createSlice({
    name: "iDoc",
    initialState,
    reducers: {
        switchObjectsVisible: (state) => {
            state.showObjects = !state.showObjects;
        },
        switchObjVisible: (state, action: PayloadAction<number>) => {
            let payload = action.payload;
            if (state.objsVis && payload >= 0 && payload < state.objsVis.length) {
                let prev = state.objsVis;
                prev[payload] = !prev[payload];
                state.objsVis = prev;
            }
        },
        setDoc: (state, action: PayloadAction<ImageDocument>) => {
            state.document = action.payload;
            state.objsVis = Array(action.payload.objects?.length).fill(true);
        },
        clearDoc: (state) => {
            state.document = undefined;
            state.objsVis = undefined;
        },
        enableAnnoMode: (state) => {
            state.annoMode = true;
            state.fetchedIdx = 0;
            state.fetchedDocs = undefined;
            state.historyIdx = 0;
            state.historyDocs = undefined;
        },
        disableAnnoMode: (state) => {
            state.annoMode = false;
            state.fetchedIdx = 0;
            state.fetchedDocs = undefined;
            state.historyIdx = 0;
            state.historyDocs = undefined;
        },
        setLabelMap: (state, action: PayloadAction<[string, Label][]>) => {
            state.labelMap = action.payload;
        },
        nextIdx: (state) => {
            if (state.historyIdx > 0) {
                let newIdx = state.historyIdx - 1;
                state.historyIdx = newIdx;
                if (state.historyDocs && newIdx < state.historyDocs.length) {
                    state.document = state.historyDocs[newIdx]
                }
            } else {
                let newIdx = state.fetchedIdx + 1;
                state.fetchedIdx = newIdx;
                if (state.fetchedDocs && newIdx < state.fetchedDocs.length) {
                    state.document = state.fetchedDocs[newIdx]
                }
            }
        },
        prevIdx: (state) => {
            if (state.fetchedIdx > 0) {
                let newIdx = state.fetchedIdx - 1;
                state.fetchedIdx = newIdx;
                if (state.fetchedDocs && newIdx < state.fetchedDocs.length) {
                    state.document = state.fetchedDocs[newIdx]
                }
            } else {
                let newIdx = state.historyIdx + 1;
                state.historyIdx = newIdx;
                if (state.historyDocs && newIdx < state.historyDocs.length) {
                    state.document = state.historyDocs[newIdx]
                }
            }
        },
        loadInNewDocs: (state, action: PayloadAction<ImageDocument[]>) => {
            let payload = action.payload
            let fetched = state.fetchedDocs;
            if (fetched) {
                let oldFetched = undefined;
                if (state.document) {
                    let untilIdx = state.fetchedIdx + 1;
                    oldFetched = fetched.slice(0, untilIdx);
                    fetched = fetched.slice(untilIdx);
                }
                let overflow = fetched.length + payload.length - state.numPrecached;
                if (overflow > 0) {
                    state.fetchedDocs = [...fetched, ...payload.slice(0, -overflow)];
                } else {
                    state.fetchedDocs = [...fetched, ...payload];
                }
                if (oldFetched) {
                    let hist = state.historyDocs;
                    if (hist) {
                        let histOvf = oldFetched.length + hist.length - state.numPrecached;
                        if (histOvf > 0) {
                            state.historyDocs = [...oldFetched, ...hist.slice(-histOvf)];
                        } else {
                            state.historyDocs = [...oldFetched, ...hist];
                        }
                    } else {
                        state.historyDocs = oldFetched;
                    }
                }
            } else {
                if (payload.length > state.numPrecached) {
                    state.fetchedDocs = payload.slice(0, state.numPrecached);
                } else {
                    state.fetchedDocs = payload;
                }
            }
            state.fetchedIdx = 0;
            state.document = state.fetchedDocs[0]
        },
        loadInOlderDocs: (state, action: PayloadAction<ImageDocument[]>) => {
            // history array is ordered from oldest to newest
            let payload = action.payload
            let hist = state.historyDocs;
            if (hist) {
                let oldHist = undefined;
                if (state.document) {
                    let untilIdx = state.historyIdx + 1;
                    oldHist = hist.slice(0, untilIdx);
                    hist = hist.slice(untilIdx);
                }
                let overflow = hist.length + payload.length - state.numPrecached;
                if (overflow > 0) {
                    state.historyDocs = [...hist, ...payload.slice(0, -overflow)];
                } else {
                    state.historyDocs = [...hist, ...payload];
                }
                if (oldHist) {
                    let fetched = state.fetchedDocs;
                    if (fetched) {
                        let fetchedOvf = oldHist.length + fetched.length - state.numPrecached;
                        if (fetchedOvf > 0) {
                            state.fetchedDocs = [...oldHist, ...fetched.slice(-fetchedOvf)];
                        } else {
                            state.fetchedDocs = [...oldHist, ...fetched];
                        }
                    } else {
                        state.fetchedDocs = oldHist;
                    }
                }
            } else {
                if (payload.length > state.numPrecached) {
                    state.historyDocs = payload.slice(0, state.numPrecached);
                } else {
                    state.historyDocs = payload;
                }
            }
            state.historyIdx = 0;
            state.document = state.historyDocs[0]
        },
    }
});

// actions
export const {
    switchObjectsVisible, switchObjVisible, setDoc,
    clearDoc, setLabelMap,
    enableAnnoMode, disableAnnoMode, nextIdx,
    prevIdx, loadInNewDocs, loadInOlderDocs,
} = idocSlice.actions;

export default idocSlice.reducer;