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
        clearNewAnnoView: (state) => {
            state.modeId = 0;
        },
    }
});

// actions
export const {
    setMode, clearNewAnnoView,
} = newAnnotationPageSlice.actions;

export default newAnnotationPageSlice.reducer;