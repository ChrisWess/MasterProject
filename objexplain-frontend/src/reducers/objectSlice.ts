import {createSlice, PayloadAction} from "@reduxjs/toolkit";

interface ObjectPageState {
    objIdx: number | undefined;
}

const initialState: ObjectPageState = {
    objIdx: undefined,
};

export const objectPageSlice = createSlice({
    name: "object",
    initialState,
    reducers: {
        setObjectIdx: (state, action: PayloadAction<number>) => {
            state.objIdx = action.payload;
        },
        clearObjectIdx: (state) => {
            state.objIdx = undefined;
        },
    }
});

// actions
export const {
    setObjectIdx, clearObjectIdx,
} = objectPageSlice.actions;

export default objectPageSlice.reducer;