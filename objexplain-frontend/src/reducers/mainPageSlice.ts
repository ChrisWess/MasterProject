import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {ProjectStats} from "../api/models/project";

interface MainPageState {
    page: number;
    maxPage: number | undefined;
    currProject: ProjectStats | undefined;
    projectFilter: string | undefined;
}

const initialState: MainPageState = {
    page: 1,
    maxPage: undefined,
    currProject: undefined,
    projectFilter: undefined,
};

export const mainPageSlice = createSlice({
    name: "mainPage",
    initialState,
    reducers: {
        nextPage: (state) => {
            const nextPageIdx = state.page + 1
            if (state.maxPage !== undefined && nextPageIdx <= state.maxPage) {
                state.page = nextPageIdx
            }
        },
        prevPage: (state) => {
            const prevPageIdx = state.page - 1
            if (prevPageIdx >= 1) {
                state.page = prevPageIdx
            }
        },
        firstPage: (state) => {
            state.page = 1
        },
        lastPage: (state) => {
            if (state.maxPage !== undefined) {
                state.page = state.maxPage
            }
        },
        setPage: (state, action: PayloadAction<number>) => {
            let page = action.payload;
            if (state.maxPage !== undefined && page >= 1 && page <= state.maxPage) {
                state.page = page
            }
        },
        setMaxPage: (state, action: PayloadAction<number | undefined>) => {
            state.maxPage = action.payload;
        },
        setProject: (state, action: PayloadAction<ProjectStats>) => {
            state.currProject = action.payload;
        },
        clearProject: (state) => {
            state.currProject = undefined;
        },
        setFilter: (state, action: PayloadAction<string>) => {
            state.projectFilter = action.payload;
        },
        clearFilter: (state) => {
            state.projectFilter = undefined;
        },
    },
});

// actions
export const {
    nextPage, prevPage, setMaxPage,
    setPage, firstPage, lastPage,
    setProject, clearProject,
    setFilter, clearFilter
} = mainPageSlice.actions;

export default mainPageSlice.reducer;