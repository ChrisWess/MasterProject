import {FC, useMemo} from "react";
import {Box, Button, List, ListItem, ListItemIcon} from "@mui/material";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import {useDispatch, useSelector} from "react-redux";
import {clearConcepts, setConceptEditIdx} from "../reducers/annotationCreateSlice";
import PhraseChip from "./PhraseChip";


interface ConceptBuilderProps {
    index: number;
    value: number;
}


const ConceptBuilderView: FC<ConceptBuilderProps> = ({value, index, ...other}) => {
    const dispatch = useDispatch();
    const concAdjectives: string[][] = useSelector((state: any) => state.newAnno.adjectives);
    const concNouns: string[][] = useSelector((state: any) => state.newAnno.nouns);
    const adjectiveIdxs: number[][] = useSelector((state: any) => state.newAnno.adjectiveIdxs);
    const nounIdxs: number[][] = useSelector((state: any) => state.newAnno.nounIdxs);
    const conceptIdx: number = useSelector((state: any) => state.newAnno.conceptEditIdx);

    const unselectedListElement = (tokens: string[], index: number) => {
        return <ListItemButton key={'concButt' + index} sx={{py: 0}}
                               onClick={() => dispatch(setConceptEditIdx(index))}>
            <ListItem divider key={'concItem' + index}>
                <ListItemIcon key={'concIcon' + index} sx={{color: 'text.secondary', width: '10px'}}>
                    {index + 1}
                </ListItemIcon>
                <ListItemText key={'concText' + index}>
                    <Typography key={'concTextInner' + index} variant='inherit' color='primary.light'>
                        {tokens.join(' ') + ' ' + concNouns[index].join(' ')}
                    </Typography>
                </ListItemText>
            </ListItem>
        </ListItemButton>
    }

    const conceptList = useMemo(() => {
        return (<List className="concepts" key="conceptList" sx={{p: 0}}>
            {!!conceptIdx && concAdjectives.slice(0, conceptIdx).map((adjectives, index) =>
                unselectedListElement(adjectives, index))}
            {concAdjectives.length > 0 && concNouns.length > 0 && (
                <ListItem divider key={'concEditItem'} sx={{color: 'white', minHeight: '50px', maxWidth: '96%', ml: 2}}>
                    <ListItemIcon key={'concEditIcon'} sx={{color: 'text.secondary'}}>
                        {conceptIdx + 1}
                    </ListItemIcon>
                    <Box>
                        {concAdjectives[conceptIdx].map(
                            (token, index) => <PhraseChip key={'concChip' + index}
                                                          token={token}
                                                          phraseIdx={adjectiveIdxs[conceptIdx][index]}
                                                          isNoun={false}
                                                          handleDelete={() => {
                                                          }}/>)}
                        {concNouns[conceptIdx].map(
                            (token, index) => <PhraseChip key={'concChip' + index}
                                                          token={token}
                                                          phraseIdx={nounIdxs[conceptIdx][index]}
                                                          isNoun={true}
                                                          handleDelete={() => {
                                                          }}/>)}
                    </Box>
                </ListItem>)}
            {concAdjectives.slice(conceptIdx + 1).map((adjectives, index) => {
                index = index + conceptIdx + 1;
                return unselectedListElement(adjectives, index);
            })}
        </List>)
    }, [concAdjectives, concNouns, adjectiveIdxs, nounIdxs, conceptIdx])

    return <div
        hidden={value !== index}
        id={'concept-builder'}
        aria-labelledby={'concept-builder'}
        style={{width: '900px'}}
        {...other}
    >
        {value === index && <Box sx={{height: '280px', p: 1}}>
            <Box sx={{display: 'flex', justifyContent: 'space-between', alignContent: 'center'}}>
                <Typography variant='h6'>List of chosen Concepts:</Typography>
                <Box width='60%'>
                    <Button sx={{width: '50%'}} onClick={() => dispatch(clearConcepts())}>Clear all Concepts</Button>
                    <Button sx={{width: '50%'}} onClick={() => {
                        // TODO: submit annotation to backend, write result into newAnnotation state and
                        //   then switch state to AnnotationViewer (modeId = 2)
                    }}>Submit Annotation</Button>
                </Box>
            </Box>
            <Box sx={{height: '230px', border: '3px solid', borderColor: '#203020'}}>
                {conceptList}
            </Box>
        </Box>}
    </div>
}

export default ConceptBuilderView
