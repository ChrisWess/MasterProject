import {FC, useEffect, useMemo, useState} from "react";
import Box from "@mui/material/Box";
import {
    Button,
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
import AlertMessage from "../components/AlertMessage";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {
    addConceptAt,
    removeConceptAt,
    setAnnotation,
    switchFeaturesVisible,
    switchFeatVisible,
    toggleHoverText
} from "../reducers/annotationSlice";
import {deleteRequest, putRequest} from "../api/requests";
import {Annotation} from "../api/models/annotation";
import {CONCEPT_COLORS} from "./AnnotationView";
import {VisualFeature} from "../api/models/feature";
import ListItemButton from "@mui/material/ListItemButton";
import LabelIcon from "@mui/icons-material/Label";
import {BBOX_COLORS} from "../document/ProjectIDocPage";
import ListItemText from "@mui/material/ListItemText";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import DeleteIcon from "@mui/icons-material/Delete";


const AnnotationControlPanel: FC = () => {
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const objIdx: number | undefined = useSelector((state: any) => state.object.objIdx);
    const annoIdx: number | undefined = useSelector((state: any) => state.annotation.annotationIdx);
    const annotation: Annotation | undefined = useSelector((state: any) => state.annotation.annotation);
    const selectedConcept: number | undefined = useSelector((state: any) => state.annotation.selectedConcept);
    const markedWords: number[] = useSelector((state: any) => state.annotation.markedWords);
    const conceptSubstrings: string[] | undefined = useSelector((state: any) => state.annotation.conceptSubstrings);
    const features: (VisualFeature | string)[] = useSelector((state: any) => state.annotation.features);
    const featsVis: boolean[] = useSelector((state: any) => state.annotation.features);

    const toProjectView = () => {
        if (project) {
            navigate('/project/' + encodeURIComponent(project.title))
        }
    }

    const toObjectView = () => {
        if (project && idoc && objIdx !== undefined) {
            navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${objIdx}`)
        }
    }

    const deleteFeature = (idx: number) => {
        console.log('Delete Feature ' + idx)
    }

    const featureList = useMemo(() => {
        // TODO: open a confirmation dialog when clicking feature deletion that also makes it possible to
        //  to transfer bboxs of the deleted feature to another or a new concept.
        if (conceptSubstrings) {
            return <List className="features" key="featureList">
                {features.map((feature, index) => {
                    if (typeof feature === 'string') {
                        // TODO: ListItemButton of concepts without feature should delegate to feature annotation
                        return <ListItem divider key={'featureItem' + index}>
                            <ListItemButton key={'featureButt' + index} sx={{py: 0}}>
                                <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'featureIcon' + index}>
                                    <LabelIcon sx={{color: CONCEPT_COLORS[index % 10], mr: 2}}/>
                                </ListItemIcon>
                                <ListItemText key={'featureText' + index}>
                                    <Typography sx={{fontSize: '14pt', color: 'text.secondary'}}>
                                        New Feature Annotation of Concept <b>{index + 1}</b>
                                    </Typography>
                                </ListItemText>
                            </ListItemButton>
                            <ListItemIcon>
                                <IconButton disabled sx={{color: 'text.secondary'}}>
                                    <VisibilityOutlinedIcon/>
                                </IconButton>
                                <IconButton aria-label="comment" disabled>
                                    <DeleteIcon sx={{color: 'text.secondary'}}/>
                                </IconButton>
                            </ListItemIcon>
                        </ListItem>
                    } else {
                        return <ListItem divider key={'featureItem' + index}>
                            <ListItemButton key={'featureButt' + index} sx={{py: 0}} onClick={() => {
                                if (project && idoc && objIdx !== undefined) {
                                    navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${objIdx}/TODO`)
                                }
                            }}>
                                <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'featureIcon' + index}>
                                    <LabelIcon sx={{color: BBOX_COLORS[index % 10], mr: 2}}/> {index + 1}
                                </ListItemIcon>
                                <ListItemText key={'featureText' + index}>
                                    <Typography variant='h6' color='primary.light'>
                                        Concept <b>{index + 1}</b>: <b>{conceptSubstrings[index]}</b>
                                    </Typography>
                                </ListItemText>
                            </ListItemButton>
                            <ListItemIcon>
                                <IconButton onClick={() => dispatch(switchFeatVisible(index))}
                                            sx={{color: 'text.secondary'}}>
                                    {featsVis[index] ?
                                        <VisibilityOffOutlinedIcon/> :
                                        <VisibilityOutlinedIcon/>}
                                </IconButton>
                                <IconButton aria-label="comment" onClick={() => deleteFeature(index)}>
                                    <DeleteIcon sx={{color: 'text.secondary'}}/>
                                </IconButton>
                            </ListItemIcon>
                        </ListItem>
                    }
                })}
            </List>
        }
        return <></>
    }, [conceptSubstrings, features, featsVis])

    const addUpdateConceptDynamic = () => {
        annotation && putRequest('/annotation',
            {
                annoId: annotation._id,
                tokenStart: markedWords[0],
                tokenEnd: markedWords[1] - 1
            }).then(data => {
            if (data) {
                let result = data.result
                let newConcepts = result.newConcepts
                if (conceptSubstrings && newConcepts.length > conceptSubstrings.length) {
                    let idx = -1
                    for (let i = 0; i < newConcepts.length; i++) {
                        let annoConcept = annotation.conceptIds[i]
                        if (annoConcept !== newConcepts[i]) {
                            idx = i;
                            break;
                        }
                    }
                    dispatch(addConceptAt(idx))
                }
                let anno = {
                    ...annotation, conceptMask: result.newMask, conceptIds: newConcepts
                }
                dispatch(setAnnotation(anno))
                // TODO: Put anno into idoc too
            }
        })
    }

    const removeConcept = () => {
        annotation && deleteRequest(`/annotation/${annotation._id}/removeConcept/${selectedConcept}`)
            .then(data => {
                if (data) {
                    dispatch(removeConceptAt(selectedConcept!))
                    let result = data.result
                    let anno = {
                        ...annotation, conceptMask: result.newMask, conceptIds: result.newConcepts
                    }
                    dispatch(setAnnotation(anno))
                    // TODO: Put anno into idoc too
                }
            })
    }

    // TODO: make another switch button for opening up a display for additional concept info (key, phraseWords, timestamps, convFilterIdx when implemented)
    // TODO: make a list for the features with the option to annotate new visual cues corresponding to the concepts

    useEffect(() => {

    }, []);

    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toObjectView}>
                    <ArrowLeftIcon sx={{fontSize: 30, ml: -1}}/> Back</IconButton>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toProjectView}>
                    <ArrowDropUpIcon sx={{fontSize: 30, ml: -1}}/> Project</IconButton>
            </Box>
            <Typography sx={{mb: 1, color: 'text.secondary'}}
                        variant='h5'>Annotation {annoIdx === undefined ? -1 : annoIdx + 1}</Typography>
            <FormGroup row sx={{ml: 1}}>
                <FormControlLabel control={<Switch defaultChecked onChange={() => dispatch(switchFeaturesVisible())}/>}
                                  label="Show Features" sx={{mr: 6}}/>
                <FormControlLabel control={<Switch defaultChecked onChange={() => dispatch(toggleHoverText())}/>}
                                  label="Hover Info above Concepts" sx={{mr: 6}}/>
            </FormGroup>
            <Divider sx={{my: 1}}/>
            <Typography variant={'h6'} sx={{mb: 1, pt: 1}}>Concept {selectedConcept !== undefined &&
                <span style={{color: CONCEPT_COLORS[selectedConcept % 10]}}>
                    {selectedConcept + 1}
                </span>}
            </Typography>
            <Box height='80px' sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                bgcolor: 'rgba(50, 50, 255, 0.08)',
                border: '2px solid',
                borderColor: 'divider',
                my: 1
            }}>
                {selectedConcept !== undefined && conceptSubstrings ?
                    <Typography sx={{bgcolor: CONCEPT_COLORS[selectedConcept % 10], px: 0.5}} variant={'h5'}>
                        <b>{conceptSubstrings[selectedConcept]}</b>
                    </Typography> :
                    <Typography sx={{color: '#303030'}} variant={'h5'}>
                        <b>None Selected</b>
                    </Typography>}
            </Box>
            <Button disabled={markedWords.length == 0} variant='outlined'
                    sx={{width: '49.5%', textTransform: 'none', mr: 0.2}}
                    onClick={addUpdateConceptDynamic}>
                Add or Update Concept (Enter Key)
            </Button>
            <Button disabled={selectedConcept === undefined} variant='outlined'
                    sx={{width: '49.5%', textTransform: 'none', ml: 0.2}}
                    onClick={removeConcept}>
                Remove Concept (Backspace Key)
            </Button>
            <Divider sx={{mt: 3}}/>
            <Box sx={{overflow: 'auto', maxHeight: 300}}>{featureList}</Box>
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default AnnotationControlPanel
