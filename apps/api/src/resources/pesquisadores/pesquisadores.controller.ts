import {
  Controller,
  Get,
  Post,
  Body,
  Patch,
  Param,
  Delete,
  ParseUUIDPipe,
  Query,
} from '@nestjs/common';
import { PesquisadoresService } from './pesquisadores.service';
import { CreatePesquisadoreDto } from './dto/create-pesquisadore.dto';
import { UpdatePesquisadoreDto } from './dto/update-pesquisadore.dto';
import { FindAllPesquisadoresDto } from './dto/find-all-pesquisadores.dto';
import { ProducoesService } from '../producoes/producoes.service';
import { FindAllProducoesDto } from '../producoes/dto/find-all-producoes.dto';

import { FindProducoesByPesquisadorQueryDto } from './dto/find-producoes-by-pesquisador-query.dto';

@Controller('pesquisadores')
export class PesquisadoresController {
  constructor(
    private readonly pesquisadoresService: PesquisadoresService, 
    private readonly producoesService:ProducoesService
  ) {}

  @Post()
  create(@Body() createPesquisadoreDto: CreatePesquisadoreDto) {
    return this.pesquisadoresService.create(createPesquisadoreDto);
  }

  @Get()
  findAll(@Query() query: FindAllPesquisadoresDto) {
    return this.pesquisadoresService.findAll(query);
  }

  @Get('busca-semantica')
  buscaSemantica(
    @Query('q') query: string, 
    @Query('page') page?: number, 
    @Query('size') size?: number
  ) {
    return this.pesquisadoresService.buscaSemantica(query, page, size);
  }

  @Get(':id')
  findOne(@Param('id', ParseUUIDPipe) id: string) {
    return this.pesquisadoresService.findOne(id);
  }

  @Get(':id/producoes')
  findProductions(
    @Param('id', ParseUUIDPipe) id: string,
    @Query() query: FindProducoesByPesquisadorQueryDto
  ) {
    const serviceQuery = query as any as FindAllProducoesDto;
    serviceQuery.pesquisadorId = id;
    return this.producoesService.findAll(serviceQuery);
  }
  @Patch(':id')
  update(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() updatePesquisadoreDto: UpdatePesquisadoreDto,
  ) {
    return this.pesquisadoresService.update(id, updatePesquisadoreDto);
  }

  @Delete(':id')
  remove(@Param('id', ParseUUIDPipe) id: string) {
    return this.pesquisadoresService.remove(id);
  }
}
