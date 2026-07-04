import { IsEnum, IsOptional, IsString, IsInt, IsUUID } from 'class-validator';
import { Type } from 'class-transformer';
import { PaginationDto } from '@/common/dto/pagination.dto';
import { TipoProducao } from '@oda/database';

export class FindAllProducoesDto extends PaginationDto {
  @IsOptional()
  @IsString()
  titulo?: string;

  @IsOptional()
  @IsInt()
  @Type(() => Number)
  ano?: number;

  @IsOptional()
  @IsEnum(TipoProducao)
  tipo?: TipoProducao;

  @IsOptional()
  @IsString()
  pesquisadorId?: string;

  @IsOptional()
  @IsString()
  grupoId?: string;
}
