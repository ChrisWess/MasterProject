import {FC, useEffect, useMemo} from "react";
import Box from "@mui/material/Box";
import {
    Button,
    ButtonGroup,
    Divider,
    FormControlLabel,
    FormGroup,
    IconButton,
    List,
    ListItem,
    ListItemIcon,
    Switch
} from "@mui/material";
import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import ArrowDropUpIcon from '@mui/icons-material/ArrowDropUp';
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {BoundingBoxCoords, VisualFeature} from "../api/models/feature";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import {
    addBbox,
    clearFeaturePage,
    clearPrevBboxs,
    initBboxVisibilities,
    setFeature,
    switchBboxVisible,
    toggleObjMovable,
    toggleShowPrevBboxs
} from "../reducers/featureSlice";
import {CONCEPT_COLORS} from "../annotation_manager/AnnotationView";
import {clearObject} from "../reducers/objectSlice";
import {clearDoc, disableAnnoMode} from "../reducers/idocSlice";
import {clearAnnotationView} from "../reducers/annotationSlice";
import {postRequest, putRequest} from "../api/requests";
import {Annotation} from "../api/models/annotation";


interface FeatureControlProps {
    resetRect: Function;
    resetZoomCallback: Function;
}

const FeatureControlPanel: FC<FeatureControlProps> = ({resetRect, resetZoomCallback}) => {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const annotation: Annotation | undefined = useSelector((state: any) => state.annotation.annotation);
    const objIdx: number | undefined = useSelector((state: any) => state.object.objIdx);
    const annoIdx: number | undefined = useSelector((state: any) => state.annotation.annotationIdx);
    const conceptIdx: number | undefined = useSelector((state: any) => state.feature.conceptIdx);
    const feature: VisualFeature | undefined = useSelector((state: any) => state.feature.visualFeature);
    const currBbox: BoundingBoxCoords | undefined = useSelector((state: any) => state.feature.currBbox);
    const bboxs: BoundingBoxCoords[] = useSelector((state: any) => state.feature.bboxs);
    const bboxsVis: boolean[] = useSelector((state: any) => state.feature.bboxsVis);
    const showPrev: boolean = useSelector((state: any) => state.feature.showPrevInput);
    const isMoveObjImg: boolean = useSelector((state: any) => state.feature.isMoveObjImg);
    const conceptSubstrings: string[] | undefined = useSelector((state: any) => state.annotation.conceptSubstrings);

    let listItemColor = conceptIdx !== undefined ? CONCEPT_COLORS[conceptIdx] : 'text.secondary'

    const toProjectView = () => {
        if (project) {
            dispatch(clearFeaturePage())
            dispatch(clearAnnotationView())
            dispatch(clearObject())
            dispatch(clearDoc())
            dispatch(disableAnnoMode())
            navigate('/project/' + encodeURIComponent(project.title))
        }
    }

    const toAnnotationView = () => {
        if (project && idoc && objIdx !== undefined && annoIdx !== undefined) {
            dispatch(clearFeaturePage())
            navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${objIdx}/${annoIdx}`)
        }
    }

    const handleSubmitFeatureUpdate = async () => {
        if (annotation && conceptIdx !== undefined) {
            let conceptId = annotation.conceptIds[conceptIdx];
            if (feature) {
                putRequest('visFeature', {
                    annoId: annotation._id, conceptId: conceptId,
                    bboxs: bboxs.map(bbox => [bbox.tlx, bbox.tly, bbox.brx, bbox.bry]),
                }).then(data => {
                    if (data && feature.bboxs) {
                        let newFeature = {...feature, bboxs: [...feature.bboxs, ...bboxs]}
                        dispatch(setFeature(newFeature))
                        dispatch(clearPrevBboxs())
                    }
                })
            } else {
                postRequest('visFeature', {
                    annoId: annotation._id, conceptId: conceptId,
                    bboxs: bboxs.map(bbox => [bbox.tlx, bbox.tly, bbox.brx, bbox.bry]),
                }).then(data => {
                    if (data) {
                        dispatch(setFeature(data.result))
                        dispatch(clearPrevBboxs())
                    }
                })
            }

        }
    }

    const editFeature = (bbox: BoundingBoxCoords, idx: number, existFlag: boolean = false) => {
        // TODO: remove the colored bounding box and draw the black editing bounding box where
        //   the corresponding bounding box was before. The button to add a BBox should now say "update bbox".
        //   When clicked, the bbox at that index should be updated and no bbox added to the list.
        console.log('Edit Feature ' + idx)
    }

    const deleteFeature = (idx: number) => {
        // TODO
        console.log('Delete Feature ' + idx)
    }

    const bboxList = useMemo(() => {
        if (bboxs.length > 0 || feature?.bboxs) {
            return <List className="fbboxs" key="fbboxsList">
                {feature?.bboxs && feature?.bboxs.map((bbox, index) => {
                    return <ListItem divider key={'fbboxItem' + index}>
                        <ListItemButton key={'fbboxButt' + index} sx={{py: 0}}
                                        onClick={() => editFeature(bbox, index, true)}>
                            <ListItemIcon sx={{color: 'text.primary', mr: 2}} key={'fbboxIcon' + index}>
                                {index + 1}
                            </ListItemIcon>
                            <ListItemText key={'fbboxText' + index}>
                                <Typography sx={{fontSize: '14pt', color: listItemColor}}>
                                    <b>Bounding Box {index + 1}</b>
                                </Typography>
                            </ListItemText>
                        </ListItemButton>
                        <ListItemIcon>
                            <IconButton onClick={() => dispatch(switchBboxVisible(index))}
                                        sx={{color: 'text.secondary'}}>
                                {bboxsVis[index] ?
                                    <VisibilityOffOutlinedIcon/> :
                                    <VisibilityOutlinedIcon/>}
                            </IconButton>
                            <IconButton aria-label="comment" onClick={() => deleteFeature(index)}>
                                <DeleteIcon sx={{color: 'text.secondary'}}/>
                            </IconButton>
                        </ListItemIcon>
                    </ListItem>
                })}
                {bboxs.map((bbox, index) => {
                    if (feature?.bboxs) {
                        index = index + feature?.bboxs.length
                    }
                    return <ListItem divider key={'bboxItem' + index}>
                        <ListItemButton key={'bboxButt' + index} sx={{py: 0}}
                                        onClick={() => editFeature(bbox, index)}>
                            <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'bboxIcon' + index}>
                                {index + 1}
                            </ListItemIcon>
                            <ListItemText key={'bboxText' + index}>
                                <Typography sx={{fontSize: '14pt', color: 'text.secondary'}}>
                                    New Bounding Box <b>{index + 1}</b>
                                </Typography>
                            </ListItemText>
                        </ListItemButton>
                        <ListItemIcon>
                            <IconButton onClick={() => dispatch(switchBboxVisible(index))}
                                        sx={{color: 'text.secondary'}}>
                                {bboxsVis[index] ?
                                    <VisibilityOffOutlinedIcon/> :
                                    <VisibilityOutlinedIcon/>}
                            </IconButton>
                            <IconButton aria-label="comment" onClick={() => deleteFeature(index)}>
                                <DeleteIcon sx={{color: 'text.secondary'}}/>
                            </IconButton>
                        </ListItemIcon>
                    </ListItem>
                })}
            </List>
        }
        return <></>
    }, [bboxs, bboxsVis, feature?.bboxs])

    useEffect(() => {
        dispatch(initBboxVisibilities())
    }, [feature?.bboxs]);

    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toAnnotationView}>
                    <ArrowLeftIcon sx={{fontSize: 30, ml: -1}}/> Back</IconButton>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toProjectView}>
                    <ArrowDropUpIcon sx={{fontSize: 30, ml: -1}}/> Project</IconButton>
            </Box>
            <Box sx={{display: 'flex', mb: 1}}>
                <Typography sx={{color: 'text.secondary'}}
                            variant='h5'>Concept {conceptIdx === undefined ? -1 : conceptIdx + 1}:&nbsp;</Typography>
                {conceptIdx !== undefined && conceptSubstrings &&
                    <Typography sx={{color: CONCEPT_COLORS[conceptIdx]}}
                                variant='h5'><b>"{conceptSubstrings[conceptIdx]}"</b></Typography>}
            </Box>
            <FormGroup row sx={{ml: 1}}>
                <FormControlLabel control={<Switch checked={showPrev}
                                                   onChange={() => dispatch(toggleShowPrevBboxs())}/>}
                                  label="Show Features"/>
            </FormGroup>
            <Divider sx={{my: 1}}/>
            <Button disabled={!currBbox} variant='outlined'
                    sx={{width: '100%', textTransform: 'none', mb: 2}}
                    onClick={() => {
                        dispatch(addBbox())
                        resetRect()
                    }}>
                Add Bounding Box to Feature
            </Button>
            <ButtonGroup sx={{width: '100%', bottom: 5}}>
                <Button onClick={() => dispatch(toggleObjMovable())} variant={isMoveObjImg ? "contained" : "outlined"}
                        sx={{flexGrow: 50}}>
                    Move / Zoom in Image
                </Button>
                <Button onClick={() => resetZoomCallback()} variant="outlined" sx={{ml: 2, flexGrow: 50}}>
                    Reset Image Position
                </Button>
            </ButtonGroup>
            <Divider sx={{mt: 3}}/>
            <Box sx={{overflow: 'auto', maxHeight: 300}}>{bboxList}</Box>
            <Button variant={"contained"} sx={{width: '100%'}} disabled={bboxs.length === 0}
                    onClick={handleSubmitFeatureUpdate}>
                Finalize Feature
            </Button>
        </Box>
    )
}

export default FeatureControlPanel
