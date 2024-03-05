import {ChangeEvent, FC, useEffect, useRef, useState} from 'react';
import {useLoaderData, useNavigate, useOutletContext, useParams} from "react-router-dom";
import {getRequest} from "../api/requests";
import {
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    Skeleton,
    TextField,
    Typography
} from "@mui/material";
import {setTitle} from "../reducers/appBarSlice";
import {useDispatch, useSelector} from "react-redux";
import {nextPage, prevPage, setMaxPage, setProject} from "../reducers/mainPageSlice";
import './Pagination.css';
import MainControlPanel from "./MainControl";
import Pagination from "./Pagination";
import ThumbnailCard from "./ThumbnailCard";


const ProjectMainPage: FC = () => {
    const {projectName} = useParams();
    const context: any = useOutletContext();
    const loadedProject: any = useLoaderData();

    const navigate = useNavigate();
    const dispatch = useDispatch();

    // global state (redux)
    const filter: string | undefined = useSelector((state: any) => state.mainPage.projectFilter);
    const page: number = useSelector((state: any) => state.mainPage.page);
    const maxPage: number = useSelector((state: any) => state.mainPage.maxPage);

    const [thumbnails, setThumbnails] = useState<string[][]>();
    const [pageText, setPageText] = useState<string>(page.toString());
    const [newDocName, setNewDocName] = useState<string>();
    const [selectedDoc, setSelectedDoc] = useState<string>();
    const [renameAction, setRenameAction] = useState<Function>();
    const [removeDocAction, setRemoveDocAction] = useState<Function>();
    const thumbnailBox = useRef(null);

    const loadThumbnails = async () => {
        if (loadedProject) {
            let data: any;
            if (filter) {
                data = await getRequest(`project/${loadedProject._id}/thumbnail/search`, page.toString(),
                    {search: filter})
            } else {
                data = await getRequest(`project/${loadedProject._id}/thumbnail`, page.toString())
            }
            if (data) {
                dispatch(setMaxPage(Math.max(data.numPages, 1)))
                return data.result
            }
        }
        return undefined
    }

    const toPrevPage = () => {
        const prevPageIdx = page - 1
        if (prevPageIdx >= 1) {
            dispatch(prevPage())
            setPageText(prevPageIdx.toString())
        }
    }

    const toNextPage = () => {
        const nextPageIdx = page + 1
        if (maxPage !== undefined && nextPageIdx <= maxPage) {
            dispatch(nextPage())
            setPageText(nextPageIdx.toString())
        }
    }

    const onArrowKeys = (event: any) => {
        const ref: any = thumbnailBox.current
        if (event.keyCode == 37) {
            toPrevPage()
        } else if (event.keyCode == 39) {
            toNextPage()
        } else if (event.keyCode == 38 && ref) {
            ref.scrollBy(0, -50)
        } else if (event.keyCode == 40 && ref) {
            ref.scrollBy(0, 50)
        }
    }

    const handleRenameDiagClose = () => {
        setRenameAction(undefined);
    };

    const handleRemoveDiagClose = () => {
        setRemoveDocAction(undefined);
    };

    const handleRenameFieldChange = (event: ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => {
        event.preventDefault();
        setNewDocName(event.target.value);
    }

    useEffect(() => {
        if (loadedProject) {
            dispatch(setProject(loadedProject))
        } else {
            navigate('/notfound404')
        }
    }, [loadedProject]);

    useEffect(() => {
        loadThumbnails().then(value => setThumbnails(value))
    }, [page, maxPage]);

    useEffect(() => {
        if (projectName) {
            dispatch(setTitle(projectName))
        }
        context.setControlPanel(<MainControlPanel/>)
    }, []);

    // TODO: Add a Switch that controls, if the search filter should be applied globally i.e. the filter and
    //  order should be the same as in the Main Page, when skipping through the individual images in the
    //  IDoc Pages (backend endpoint for this functionality does not exist yet)
    return (
        <>
            <Box sx={{color: 'background.paper'}}>
                <Box minHeight='740px' sx={{mb: 2}} onKeyDownCapture={onArrowKeys} tabIndex={-1}>
                    <Box maxHeight='740px' sx={{display: 'flex', flexWrap: 'wrap', overflow: 'auto', mb: 2}}
                         ref={thumbnailBox}>
                        {!!thumbnails ?
                            (thumbnails.length > 0 ?
                                    thumbnails?.map((thumb) => <ThumbnailCard key={thumb[0]} docId={thumb[0]}
                                                                              name={thumb[1]} data={thumb[2]}
                                                                              setSelectedDoc={setSelectedDoc}
                                                                              setRenameAction={setRenameAction}
                                                                              setRemoveDocAction={setRemoveDocAction}/>) :
                                    <Typography sx={{color: 'text.secondary'}}>
                                        Your Project is currently empty! Use the Dataset Import or upload individual
                                        images.
                                    </Typography>
                            )
                            : <>
                                <Skeleton variant="rectangular" width={'auto'} height={20} sx={{mt: '5px'}}/>
                                <Skeleton variant="rectangular" sx={{mt: '10px'}} width={'auto'} height={20}/>
                                <Skeleton variant="rectangular" sx={{mt: '10px'}} width={'auto'} height={20}/>
                            </>}
                    </Box>
                </Box>
                <Pagination pageText={pageText} setPageText={setPageText} toPrevPage={toPrevPage}
                            toNextPage={toNextPage}/>
            </Box>

            <Dialog open={selectedDoc !== undefined && renameAction !== undefined}
                    onClose={handleRenameDiagClose}>
                <DialogTitle sx={{color: 'primary'}}>Rename Document {selectedDoc}</DialogTitle>
                <DialogContent>
                    <TextField id="filled-basic"
                               label='New Name'
                               size='small'
                               variant="outlined"
                               onChange={handleRenameFieldChange}
                               value={newDocName}
                               sx={{
                                   mt: 1, width: '100%',
                                   "& .MuiOutlinedInput-notchedOutline": {
                                       borderColor: "#9090C0",
                                   }
                               }}
                    />
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" color="primary" sx={{marginRight: '60%'}}
                            disabled={newDocName?.trim().length == 0}
                            onClick={() => {
                                if (renameAction) {
                                    renameAction(newDocName);
                                    handleRenameDiagClose();
                                }
                            }}>rename</Button>
                    <Button onClick={handleRenameDiagClose}>Cancel</Button>
                </DialogActions>
            </Dialog>

            <Dialog open={selectedDoc !== undefined && removeDocAction !== undefined}
                    onClose={handleRemoveDiagClose}>
                <DialogTitle sx={{color: 'red'}}></DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Do you really want to delete Document {selectedDoc}?
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" color="error" sx={{marginRight: '60%'}}
                            onClick={() => {
                                if (removeDocAction) {
                                    removeDocAction();
                                    handleRemoveDiagClose();
                                    dispatch(setMaxPage(undefined));
                                }
                            }}>delete</Button>
                    <Button onClick={handleRemoveDiagClose}>Cancel</Button>
                </DialogActions>
            </Dialog>
        </>
    )
}

export default ProjectMainPage;
