import {createSlice, PayloadAction} from "@reduxjs/toolkit";

interface NewObjectPageState {
    isZooming: boolean;
    zoomResetter: Function | undefined;
}

const initialState: NewObjectPageState = {
    isZooming: true,
    zoomResetter: undefined,
};

export const newObjectPageSlice = createSlice({
    name: "newObj",
    initialState,
    reducers: {
        switchZooming: (state) => {
            state.isZooming = !state.isZooming;
        },
        setZoomResetter: (state, action: PayloadAction<Function>) => {
            state.zoomResetter = action.payload;
        },
    }
});

// actions
export const {
    switchZooming, setZoomResetter,
} = newObjectPageSlice.actions;

export default newObjectPageSlice.reducer;