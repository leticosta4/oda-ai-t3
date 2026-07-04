import { OmitType } from '@nestjs/mapped-types';
import { FindAllProducoesDto } from '../../producoes/dto/find-all-producoes.dto';

export class FindProducoesByPesquisadorQueryDto extends OmitType(FindAllProducoesDto, [
  'pesquisadorId',
] as const) {}
