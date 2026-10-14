import { render, screen } from '@testing-library/react';
import { it, expect } from 'vitest';
import { MemoryRouter } from 'react-router';
import { LearningHelp } from '@/features/learning/LearningHelp';
it('opens the single question workspace with captured learning identifiers',()=>{render(<MemoryRouter><LearningHelp contentId={11} planId={21} sessionId={31} contextRevision={null} active/></MemoryRouter>);expect(screen.getByRole('link')).toHaveAttribute('href','/tutor?content_id=11&session_id=31&plan_id=21');expect(screen.queryByRole('textbox')).not.toBeInTheDocument();});
it('hides the contextual entry while authentication is suspended',()=>{render(<MemoryRouter><LearningHelp contentId={11} planId={null} sessionId={31} contextRevision={null} active={false}/></MemoryRouter>);expect(screen.queryByRole('link')).not.toBeInTheDocument();});
