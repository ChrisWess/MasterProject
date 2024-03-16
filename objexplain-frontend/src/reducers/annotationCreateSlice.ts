import {createSlice, PayloadAction} from "@reduxjs/toolkit";

interface NewAnnotationPageState {
    modeId: number;
}

const initialState: NewAnnotationPageState = {
    modeId: 0,
};

export const newAnnotationPageSlice = createSlice({
    name: "newAnno",
    initialState,
    reducers: {
        setMode: (state, action: PayloadAction<number>) => {
            state.modeId = action.payload;
        },
    }
});

// actions
export const {
    setMode,
} = newAnnotationPageSlice.actions;

export default newAnnotationPageSlice.reducer;