import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {DetectedObject} from "../api/models/object";
import {Label} from "../api/models/label";

interface ObjectPageState {
    objIdx: number | undefined;
    detObj: DetectedObject | undefined;
    objectLabel: Label | undefined;
}

const initialState: ObjectPageState = {
    objIdx: undefined,
    detObj: undefined,
    objectLabel: undefined,
};

export const objectPageSlice = createSlice({
    name: "object",
    initialState,
    reducers: {
        setObjectIdx: (state, action: PayloadAction<number>) => {
            state.objIdx = action.payload;
        },
        setObject: (state, action: PayloadAction<DetectedObject>) => {
            state.detObj = action.payload;
        },
        setObjectLabel: (state, action: PayloadAction<Label>) => {
            state.objectLabel = action.payload;
        },
        clearObject: (state) => {
            state.objIdx = undefined;
            state.objectLabel = undefined;
            state.detObj = undefined;
        },
    }
});

// actions
export const {
    setObjectIdx, setObject, setObjectLabel,
    clearObject,
} = objectPageSlice.actions;

export default objectPageSlice.reducer;