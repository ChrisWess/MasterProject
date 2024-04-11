import {FC, useEffect, useMemo, useState} from "react";
import {Box, ButtonGroup, Divider, List, ListItem, ListItemIcon} from "@mui/material";
import Typography from "@mui/material/Typography";
import {Concept} from "../api/models/concept";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import AddIcon from "@mui/icons-material/Add";
import {getRequest, postRequest} from "../api/requests";
import {CorpusWord} from "../api/models/corpus";
import PhraseChip from "./PhraseChip";
import ButtonTextfield from "../components/ButtonTextfield";
import {useDispatch, useSelector} from "react-redux";
import {
    addAdjective,
    addNewConceptDraft,
    addNoun,
    addSelectedConcept,
    pushSuggestedConcepts,
    selectConceptIdx,
    setSuggestedAdjectives,
    setSuggestedConcepts,
    setSuggestedNouns
} from "../reducers/annotationCreateSlice";
import Button from "@mui/material/Button";
import {Label} from "../api/models/label";


export const loadSuggestedConcepts = async (labelId: string, page: number) => {
    return await getRequest(`stats/concept/tfIdf/label/${labelId}`, page.toString())
}


export const loadSuggestedAdjectives = async (labelId: string) => {
    return await getRequest('stats/corpus/adj/tfIdf/label', labelId, {limit: 15})
}


export const loadSuggestedNouns = async (labelId: string) => {
    return await getRequest('stats/corpus/noun/tfIdf/label', labelId, {limit: 15})
}


const ConceptsController: FC = () => {
    const [conceptPageIdx, setConceptPageIdx] = useState<number>(0);

    const dispatch = useDispatch();
    const objectLabel: Label | undefined = useSelector((state: any) => state.object.objectLabel);
    const selectedConceptIdx: number | undefined = useSelector((state: any) => state.newAnno.selectedConceptIdx);
    const conceptsUsed: boolean[] = useSelector((state: any) => state.newAnno.conceptsSelected);
    const concepts: Concept[] = useSelector((state: any) => state.newAnno.suggestedConcepts);
    const adjectives: CorpusWord[] | undefined = useSelector((state: any) => state.newAnno.suggestedAdjectives);
    const nouns: CorpusWord[] | undefined = useSelector((state: any) => state.newAnno.suggestedNouns);

    const suggestedConcepts = useMemo(() => {
        return (<List className="suggestedConcepts" key="suggestionList"
                      sx={{bgcolor: '#252525', p: 0}}>
            {concepts && conceptsUsed && concepts.map((concept, index) =>
                <ListItem divider key={'concSelectItem' + index}
                          sx={{
                              height: '40px',
                              bgcolor: (selectedConceptIdx !== undefined && selectedConceptIdx === index) ? '#405540' : ''
                          }}>
                    <ListItemButton key={'concSelectButt' + index} sx={{py: 0}}
                                    onClick={() => dispatch(selectConceptIdx(index))}
                                    disabled={conceptsUsed[index]}>
                        <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'concSelectIcon' + index}>
                            {index + 1}
                        </ListItemIcon>
                        <ListItemText key={'concSelectText' + index}>
                            <Typography variant='h6' color='primary.light'>
                                <b>{concept.phraseWords.join(' ')}</b>
                            </Typography>
                        </ListItemText>
                        <ListItemIcon>
                            <AddIcon sx={{color: 'text.primary'}}/>
                        </ListItemIcon>
                    </ListItemButton>
                </ListItem>)}
            <ListItemButton key={'conceptLoader'} sx={{py: 0, height: '40px'}}
                            onClick={() => {
                                if (objectLabel) {
                                    let newPage = conceptPageIdx + 1
                                    loadSuggestedConcepts(objectLabel._id, newPage)
                                        .then(data => data && dispatch(pushSuggestedConcepts(data.result.map((res: any) => res.concept))))
                                    setConceptPageIdx(newPage)
                                }
                            }}>
                <ListItem divider key={'conceptLoadItem'} sx={{height: '40px'}}>
                    <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'conceptLoadIcon'}>
                        <AddIcon/>
                    </ListItemIcon>
                    <ListItemText key={'conceptLoadText'}>
                        <Typography variant='h6' color='primary.light'>
                            Load more Concepts
                        </Typography>
                    </ListItemText>
                </ListItem>
            </ListItemButton>
        </List>)
    }, [concepts, selectedConceptIdx, conceptsUsed])

    const handleChipClick = (word: CorpusWord) => {
        let input: [string, number] = [word.text, word.index]
        word.nounFlag ? dispatch(addNoun(input)) : dispatch(addAdjective(input))
    }

    const customSubmitFactory = (isNoun: boolean) => {
        return (text: string) => {
            postRequest('corpus', {word: text, isNoun: isNoun}).then(data => {
                if (data) {
                    let result: CorpusWord = data.result
                    let input: [string, number] = [result.text, result.index]
                    isNoun ? dispatch(addNoun(input)) : dispatch(addAdjective(input))
                }
            })
        }
    }

    const suggestedAdjectives = useMemo(() => {
        return <Box sx={{bgcolor: '#252525', width: '100%', p: '5px', border: '2px solid', borderColor: '#161616'}}>
            <Typography variant='subtitle2' sx={{color: '#c2c2c2'}}>Select suggested adjectives:</Typography>
            <Box sx={{height: '73px', overflow: 'auto'}}>
                {adjectives && adjectives.map((word, index) => <PhraseChip key={'adjChip' + index}
                                                                           token={word.text}
                                                                           phraseIdx={word.index} isNoun={false}
                                                                           handleClick={() => handleChipClick(word)}/>)}
            </Box>
            <ButtonTextfield tfLabel='Custom Adjective' buttonText='Add to Concept'
                             submitFunc={customSubmitFactory(false)} clearOnSubmit/>
        </Box>
    }, [adjectives])

    const suggestedNouns = useMemo(() => {
        return <Box sx={{bgcolor: '#252525', width: '100%', p: '5px', border: '2px solid', borderColor: '#161616'}}>
            <Typography variant='subtitle2' sx={{color: '#c2c2c2'}}>Select suggested nouns:</Typography>
            <Box sx={{height: '73px', overflow: 'auto'}}>
                {nouns && nouns.map((word, index) => <PhraseChip key={'nounChip' + index}
                                                                 token={word.text}
                                                                 phraseIdx={word.index} isNoun={true}
                                                                 handleClick={() => handleChipClick(word)}/>)}
            </Box>
            <ButtonTextfield tfLabel='Custom Noun' buttonText='Add to Concept'
                             submitFunc={customSubmitFactory(true)} clearOnSubmit/>
        </Box>
    }, [nouns])

    useEffect(() => {
        if (objectLabel) {
            let labelId = objectLabel._id
            !adjectives && loadSuggestedAdjectives(labelId)
                .then(data => data && dispatch(setSuggestedAdjectives(data.result.map((res: any) => res.word))))
            !nouns && loadSuggestedNouns(labelId)
                .then(data => data && dispatch(setSuggestedNouns(data.result.map((res: any) => res.word))))
        }
    }, [objectLabel]);

    useEffect(() => {
        if (objectLabel && concepts.length === 0) {
            setConceptPageIdx(0)
            loadSuggestedConcepts(objectLabel._id, 0)
                .then(data => data && dispatch(setSuggestedConcepts(data.result.map((res: any) => res.concept))))
        }
    }, [objectLabel, concepts]);

    return <>
        <Typography variant='h6'>Select suggested Concepts or build new ones</Typography>
        <Divider sx={{my: 1}}/>
        <Typography variant='subtitle1' sx={{mb: 0.6, color: '#c2c2c2'}}>Choose suggested, already existing
            concepts:</Typography>
        <Box sx={{height: '145px', overflow: 'auto', border: '2px solid', mb: 0.5, borderColor: '#161616'}}>
            {suggestedConcepts}
        </Box>
        <ButtonGroup sx={{width: '100%', height: '30px', mb: 1}}>
            <Button sx={{textTransform: 'none', fontSize: '12pt', width: '49.5%', mr: 1}}
                    variant='contained' onClick={() => dispatch(addSelectedConcept())}>
                <b>Add Concept to Annotation</b>
            </Button>
            <Button sx={{textTransform: 'none', fontSize: '12pt', width: '49.5%'}}
                    variant='contained' onClick={() => dispatch(addNewConceptDraft())}>
                <b>New empty Concept Draft</b>
            </Button>
        </ButtonGroup>
        <Divider sx={{mb: 1}}/>
        <Typography variant='h6' sx={{mb: 1}}>Build a custom concept:</Typography>
        {suggestedAdjectives}
        <Divider/>
        {suggestedNouns}
    </>
}

export default ConceptsController
