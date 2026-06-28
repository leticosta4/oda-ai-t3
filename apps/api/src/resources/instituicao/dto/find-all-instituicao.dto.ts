import { IsOptional, IsString } from 'class-validator';
import { PaginationDto } from '@/common/dto/pagination.dto';

export class FindAllInstituicaoDto extends PaginationDto {
  @IsOptional()
  @IsString()
  nome?: string;
}
