import {createSlice, PayloadAction} from "@reduxjs/toolkit";

interface OperationsState {
    unsavedChanges: boolean;
    cacheSize: number;
    docIds: string[];
    ops: string[][];
}

const initialState: OperationsState = {
    unsavedChanges: false,
    cacheSize: 3,
    docIds: [],
    ops: []
};

export const operationsSlice = createSlice({
    name: "operations",
    initialState,
    reducers: {
        addDoc: (state, action: PayloadAction<string>) => {
            if (state.docIds.length < state.cacheSize) {
                state.docIds.push(action.payload);
            } else {
                state.docIds.splice(0, 1);
                state.docIds.push(action.payload);
            }
        },
        removeDoc: (state, action: PayloadAction<number>) => {
            if (state.docIds.length > 0) {
                state.docIds.splice(action.payload, 1);
            }
        },
        clearChanges: (state) => {
            state.unsavedChanges = false
            state.ops = []
        },
    },
});

export const {addDoc, removeDoc, clearChanges} = operationsSlice.actions;

export default operationsSlice.reducer;
