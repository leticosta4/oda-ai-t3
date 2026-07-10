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
import type { UUID } from "node:crypto";
import { ProducoesService } from './producoes.service';
import { CreateProducoeDto } from './dto/create-producoe.dto';
import { UpdateProducoeDto } from './dto/update-producoe.dto';
import { FindAllProducoesDto } from './dto/find-all-producoes.dto';

@Controller('producoes')
export class ProducoesController {
  constructor(private readonly producoesService: ProducoesService) {}

  @Post()
  create(@Body() createProducoeDto: CreateProducoeDto) {
    return this.producoesService.create(createProducoeDto);
  }

  @Get()
  findAll(@Query() query: FindAllProducoesDto) {
    return this.producoesService.findAll(query);
  }

  @Get('busca-semantica')
  buscaSemantica(
    @Query('q') query: string, 
    @Query('page') page?: number, 
    @Query('size') size?: number
  ) {
    return this.producoesService.buscaSemantica(query, page, size);
  }

  @Get(':id')
  findOne(@Param('id', ParseUUIDPipe) id: string) {
    return this.producoesService.findOne(id);
  }

  @Patch(':id')
  update(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() updateProducoeDto: UpdateProducoeDto,
  ) {
    return this.producoesService.update(id, updateProducoeDto);
  }

  @Delete(':id')
  remove(@Param('id', ParseUUIDPipe) id: string) {
    return this.producoesService.remove(id);
  }
}
