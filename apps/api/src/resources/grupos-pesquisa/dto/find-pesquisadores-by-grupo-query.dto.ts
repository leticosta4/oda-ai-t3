import { OmitType } from '@nestjs/mapped-types';
import { FindAllPesquisadoresDto } from '../../pesquisadores/dto/find-all-pesquisadores.dto';

export class FindPesquisadoresByGrupoQueryDto extends OmitType(FindAllPesquisadoresDto, [
  'grupoPesquisaId',
] as const) {}
