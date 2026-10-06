import {render,screen} from '@testing-library/react';import Home from '../app/page';import {describe,it,expect} from 'vitest';
describe('home',()=>it('shows the primary action',()=>{render(<Home/>);expect(screen.getByRole('link',{name:/analyse a product/i})).toBeInTheDocument()}));
