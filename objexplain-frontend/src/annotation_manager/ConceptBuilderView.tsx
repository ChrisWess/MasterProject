import {FC, useMemo} from "react";
import {Box, Chip, List, ListItem, ListItemIcon} from "@mui/material";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import {useDispatch, useSelector} from "react-redux";
import {setConceptEditIdx} from "../reducers/annotationCreateSlice";
import Tooltip from "@mui/material/Tooltip";


interface PhraseChipProps {
    token: string;
    phraseIdx: number;
    isNoun: boolean;
    handleDelete: any;
}


const PhraseChip: FC<PhraseChipProps> = ({token, phraseIdx, isNoun, handleDelete}) => {
    token = isNoun ? token.charAt(0).toUpperCase() + token.substring(1).toLowerCase() : token.toLowerCase()
    // TODO: nouns clickable to select root noun?
    return <Tooltip title={'phrase word ' + phraseIdx}>
        <Chip label={token} variant="outlined" color={isNoun ? 'primary' : 'success'}
              onDelete={handleDelete}/>
    </Tooltip>
}


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
                <ListItemIcon sx={{color: 'text.secondary', width: '10px'}} key={'concIcon' + index}>
                    {index + 1}
                </ListItemIcon>
                <ListItemText key={'concText' + index}>
                    <Typography variant='inherit' color='primary.light'>
                        {tokens.join(' ') + ' ' + concNouns[index].join(' ')}
                    </Typography>
                </ListItemText>
            </ListItem>
        </ListItemButton>
    }

    const conceptList = useMemo(() => {
        return (<List className="concepts" key="conceptList">
            {conceptIdx && concAdjectives.slice(0, conceptIdx - 1).map((adjectives, index) =>
                unselectedListElement(adjectives, index))}
            <ListItem divider key={'concEditItem' + index} sx={{color: 'white'}}>
                <ListItemIcon sx={{color: 'text.secondary', width: '10px'}} key={'concEditIcon' + index}>
                    {index + 1}
                </ListItemIcon>
                {concAdjectives[conceptIdx].map((token, index) => <PhraseChip token={token}
                                                                              phraseIdx={adjectiveIdxs[conceptIdx][index]}
                                                                              isNoun={false}
                                                                              handleDelete={() => {
                                                                              }}/>)}
                {concNouns[conceptIdx].map((token, index) => <PhraseChip token={token}
                                                                         phraseIdx={nounIdxs[conceptIdx][index]}
                                                                         isNoun={true}
                                                                         handleDelete={() => {
                                                                         }}/>)}
            </ListItem>
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
        {...other}
    >
        {value === index && <Box sx={{p: 1}}>
            <Typography variant='h5'>List of chosen Concepts:</Typography>
            {conceptList}
        </Box>}
    </div>
}

export default ConceptBuilderView
